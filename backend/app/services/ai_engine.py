"""
AI Engine Service
==================

This is the **brain** of BotForge -- the central service that orchestrates the
entire AI response pipeline. When a customer sends a message, this service
coordinates multiple steps to produce a high-quality, grounded answer.

The Full Pipeline (5 steps):
----------------------------

1. **Intent Classification** -- Determine what the customer wants.
   The message is sent to the LLM with a specialized prompt that classifies it
   into one of these categories: FAQ, Booking, Order, Complaint, Chitchat, or
   Unknown. This helps downstream logic (e.g., complaints get escalated more
   aggressively).

2. **RAG Search** -- Find relevant knowledge base content.
   The customer's message is embedded into a vector and searched against the
   bot's ChromaDB collection. The top 5 most relevant document chunks are
   retrieved. These chunks give the LLM factual context to answer from.

3. **Answer Generation** -- Produce the actual response.
   The LLM receives the system prompt (bot personality, rules, tone), the
   retrieved document chunks as context, the conversation history, and the
   customer's message. It generates an answer grounded in the provided context,
   citing sources where possible.

4. **Confidence Scoring** -- How sure are we about this answer?
   The system extracts a self-reported confidence score from the LLM's response
   (it's asked to include "[Confidence: X/10]" in its reply). If the LLM didn't
   include one, a heuristic estimate is used based on whether relevant chunks
   were found.

5. **Handoff Decision** -- Should a human take over?
   Based on the confidence score and intent, the system decides whether to
   escalate the conversation to a human agent. Low confidence (<50%) always
   triggers handoff. Complaints with moderate confidence (<70%) also trigger
   handoff, since unhappy customers deserve extra care.

How it fits in the architecture:
- Called by the chat/webhook API routes after a message is received and
  normalized.
- Depends on **llm_client.py** for all LLM interactions.
- Depends on **rag_pipeline.py** for knowledge base searches.
- Its output (answer, confidence, handoff decision) drives what happens next:
  sending the response, escalating, or notifying agents.
"""

import re
import yaml
import os
from typing import AsyncIterator

from app.services.llm_client import LLMClient
from app.services.rag_pipeline import RAGPipeline
from app.services.bot_genres import get_genre, build_system_prompt


def _strip_confidence_tag(answer: str) -> str:
    """Remove the self-rating tag ("[Confidence: 8/10]") from the visible answer."""
    return re.sub(r"\s*\[Confidence:\s*\d+/10\]\s*", " ", answer).strip()


class AIEngine:
    """
    Core AI processing pipeline: intent -> RAG -> answer -> confidence -> handoff.

    This class ties together the LLM client and RAG pipeline to form the
    complete message-processing workflow. It also manages prompt templates
    loaded from YAML files, allowing bot owners to customize the AI's behavior.

    Attributes:
        llm (LLMClient): The LLM client used for all language model calls.
        rag (RAGPipeline): The RAG pipeline used for knowledge base queries.
        _prompts (dict): Cache of loaded prompt templates (loaded from YAML files
                         in the app/prompts/ directory).
    """

    def __init__(self):
        """
        Initialize the AI engine with an LLM client and RAG pipeline.

        Both are created fresh for each AIEngine instance. The LLM client
        will use whichever provider is configured in settings (Claude, OpenAI,
        or Ollama).
        """
        self.llm = LLMClient()
        self.rag = RAGPipeline()
        self._prompts = {}  # Cache for prompt templates loaded from YAML files

    # -------------------------------------------------------------------------
    # Prompt template loading
    # -------------------------------------------------------------------------

    def _load_prompt(self, name: str) -> str:
        """
        Load a prompt template from a YAML file in the app/prompts/ directory.

        Prompt templates allow customization of how the LLM behaves for different
        tasks (intent classification, answer generation, etc.). They are stored
        as YAML files with a "template" key containing the prompt text.

        Results are cached in self._prompts so each file is read only once.

        Args:
            name: The name of the prompt (e.g., "intent_classifier"), which
                  corresponds to the file "app/prompts/intent_classifier.yaml".

        Returns:
            The prompt template string, or "" if the file doesn't exist.
        """
        if name not in self._prompts:
            prompt_path = os.path.join(
                os.path.dirname(__file__), "..", "prompts", f"{name}.yaml"
            )
            if os.path.exists(prompt_path):
                with open(prompt_path) as f:
                    data = yaml.safe_load(f)
                    self._prompts[name] = data.get("template", "")
            else:
                self._prompts[name] = ""
        return self._prompts[name]

    # -------------------------------------------------------------------------
    # Main pipeline: process_message
    # -------------------------------------------------------------------------

    async def process_message(
        self,
        bot_id: str,
        message: str,
        conversation_history: list[dict],
        bot_config: dict,
    ) -> dict:
        """
        Run the full AI pipeline on an incoming customer message.

        This is the main entry point called by the chat API. It orchestrates
        all 5 steps of the pipeline in sequence:

        Step 1 - Classify Intent:
            Send the message to the LLM to determine what the customer wants
            (FAQ, Booking, Order, Complaint, Chitchat, or Unknown).

        Step 2 - RAG Search:
            Search the bot's knowledge base (ChromaDB) for the top 5 most
            relevant document chunks that might help answer the question.

        Step 3 - Generate Answer:
            Send the question, retrieved chunks, conversation history, and
            bot configuration to the LLM to generate a grounded response.

        Step 4 - Score Confidence:
            Extract or estimate a confidence score (0.0 to 1.0) indicating
            how reliable the answer is.

        Step 5 - Handoff Decision:
            Determine whether this conversation should be escalated to a
            human agent based on confidence and intent.

        Args:
            bot_id: The ID of the bot handling this conversation.
            message: The customer's message text.
            conversation_history: List of previous messages in this conversation,
                                  each with "role" and "content" keys.
            bot_config: The bot's configuration dict containing name, tone,
                        custom_rules, and other settings.

        Returns:
            A dict containing:
            - "answer" (str): The generated response text.
            - "sources" (list): The document chunks used as context.
            - "confidence" (float): Confidence score from 0.0 to 1.0.
            - "intent" (str): The classified intent category.
            - "handoff" (bool): Whether to escalate to a human agent.
            - "chunks_used" (int): Number of knowledge base chunks used.
        """
        # Step 1: Classify what the customer is asking about
        intent = await self.classify_intent(message)

        # Step 2: Search the knowledge base for relevant document chunks
        chunks = await self.rag.query(bot_id, message, top_k=5)

        # Step 3: Generate an answer using the LLM with the retrieved context
        answer_data = await self.generate_answer(
            query=message,
            chunks=chunks,
            history=conversation_history,
            bot_config=bot_config,
        )

        # Step 4: Determine how confident we are in the answer (parsed from the
        # raw answer, before the tag is stripped for display)
        confidence = await self.score_confidence(answer_data["answer"], chunks)

        # Step 5: Decide if a human should take over. Genres like tutor/coding/
        # character never hand off — they answer as best they can.
        genre = get_genre(bot_config.get("bot_type"))
        handoff = genre["allow_handoff"] and await self.should_handoff(
            confidence, intent, bot_config.get("custom_rules", [])
        )

        return {
            "answer": _strip_confidence_tag(answer_data["answer"]),
            "sources": answer_data["sources"],
            "confidence": confidence,
            "intent": intent,
            "handoff": handoff,
            "chunks_used": len(chunks),
        }

    # -------------------------------------------------------------------------
    # Step 1: Intent Classification
    # -------------------------------------------------------------------------

    async def classify_intent(self, message: str) -> str:
        """
        Classify the customer's message into an intent category.

        The LLM is given a specialized prompt that instructs it to output
        exactly one category name. This uses a very low temperature (0.1) and
        short max_tokens (20) to get a fast, deterministic, single-word answer.

        Intent categories:
        - FAQ: General questions about the business/product.
        - Booking: Requests to schedule/reserve something.
        - Order: Questions about orders, shipping, tracking.
        - Complaint: Negative feedback, problems, frustration.
        - Chitchat: Casual conversation, greetings, small talk.
        - Unknown: Doesn't fit any of the above.

        The intent is used later in the pipeline for:
        - Handoff decisions (Complaints are escalated more aggressively).
        - Analytics (track what types of questions customers ask).

        Args:
            message: The raw customer message text.

        Returns:
            A string with the intent category name (e.g., "FAQ", "Complaint").
        """
        # Try to load a custom prompt template; fall back to a built-in default
        prompt_template = self._load_prompt("intent_classifier")
        system_prompt = prompt_template or (
            "You are an intent classifier. Classify the user message into exactly one of these "
            "categories: FAQ, Booking, Order, Complaint, Chitchat, Unknown. "
            "Respond with ONLY the category name, nothing else."
        )

        result = await self.llm.chat(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": message}],
            temperature=0.1,   # Very low for deterministic classification
            max_tokens=20,     # We only need a single word back
        )
        return result.strip()

    # -------------------------------------------------------------------------
    # Step 3: Answer Generation
    # -------------------------------------------------------------------------

    async def generate_answer(
        self,
        query: str,
        chunks: list[dict],
        history: list[dict],
        bot_config: dict,
    ) -> dict:
        """
        Generate an answer using the LLM with RAG context and conversation history.

        This method builds a rich system prompt that includes:
        - The bot's name and personality/tone.
        - Any custom rules the bot owner has defined.
        - The retrieved knowledge base chunks (formatted as numbered sources).
        - Recent conversation history (last 10 messages) for continuity.
        - Instructions to cite sources, stay in character, and self-rate confidence.

        The LLM then generates a response grounded in the provided context.
        If no relevant chunks were found, the LLM is instructed to honestly
        say it doesn't know rather than hallucinate.

        Args:
            query: The customer's current message.
            chunks: List of relevant document chunks from RAG search. Each chunk
                    has "content", "metadata", and "distance" keys.
            history: Previous messages in this conversation (role + content dicts).
            bot_config: Bot settings including "name", "tone", and "custom_rules".

        Returns:
            A dict with:
            - "answer" (str): The generated response text.
            - "sources" (list): Metadata about the chunks that were provided as
              context (index, truncated content, metadata).
        """
        # Build context from RAG chunks -- format each chunk with a source number
        # so the LLM can reference them in its answer (e.g., "Based on Source 1...")
        context_parts = []
        sources = []
        for i, chunk in enumerate(chunks):
            context_parts.append(f"[Source {i + 1}] {chunk['content']}")
            sources.append({
                "index": i + 1,
                "content": chunk["content"][:200],  # Truncate for the response metadata
                "metadata": chunk.get("metadata", {}),
            })

        # If no chunks were found, tell the LLM there are no documents to reference
        context_text = "\n\n".join(context_parts) if context_parts else "No relevant documents found."

        # Build a readable conversation history (last 10 messages to avoid token overflow)
        history_text = ""
        if history:
            for msg in history[-10:]:
                role = msg.get("role", "customer")
                content = msg.get("content", "")
                history_text += f"{role}: {content}\n"

        # Assemble the genre-aware system prompt (identity, grounding rules, and
        # handoff/confidence behavior all depend on the bot's genre).
        system_prompt = build_system_prompt(bot_config, context_text, history_text)

        # Send to LLM -- temperature 0.3 for consistent but slightly creative answers
        answer = await self.llm.chat(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": query}],
            temperature=0.3,
        )

        return {"answer": answer, "sources": sources}

    # -------------------------------------------------------------------------
    # Streaming variant: yields the answer token-by-token
    # -------------------------------------------------------------------------

    async def stream_message(
        self,
        bot_id: str,
        message: str,
        conversation_history: list[dict],
        bot_config: dict,
    ) -> AsyncIterator[dict]:
        """
        Streaming counterpart of `process_message`.

        Yields a sequence of event dicts so the SSE endpoint can forward them
        to the browser as they happen:

        1. {"type": "intent",  "intent": "FAQ"}
        2. {"type": "sources", "sources": [...], "chunks_used": N}
        3. {"type": "token",   "delta": "..."}     # many of these
        4. {"type": "done",    "answer": "...", "confidence": 0.0..1.0,
            "intent": "...", "handoff": bool}

        The full answer text is accumulated locally so the final "done" event
        can include confidence + handoff (which both depend on the full text).
        """
        intent = await self.classify_intent(message)
        yield {"type": "intent", "intent": intent}

        chunks = await self.rag.query(bot_id, message, top_k=5)

        sources = []
        context_parts = []
        for i, chunk in enumerate(chunks):
            context_parts.append(f"[Source {i + 1}] {chunk['content']}")
            sources.append({
                "index": i + 1,
                "content": chunk["content"][:200],
                "metadata": chunk.get("metadata", {}),
            })
        yield {"type": "sources", "sources": sources, "chunks_used": len(chunks)}

        context_text = "\n\n".join(context_parts) if context_parts else "No relevant documents found."
        history_text = ""
        if conversation_history:
            for msg in conversation_history[-10:]:
                history_text += f"{msg.get('role', 'customer')}: {msg.get('content', '')}\n"

        system_prompt = build_system_prompt(bot_config, context_text, history_text)

        full_answer_parts: list[str] = []
        async for delta in self.llm.chat_stream(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": message}],
            temperature=0.3,
        ):
            full_answer_parts.append(delta)
            yield {"type": "token", "delta": delta}

        answer = "".join(full_answer_parts)
        confidence = await self.score_confidence(answer, chunks)
        genre = get_genre(bot_config.get("bot_type"))
        handoff = genre["allow_handoff"] and await self.should_handoff(
            confidence, intent, bot_config.get("custom_rules", [])
        )

        yield {
            "type": "done",
            "answer": _strip_confidence_tag(answer),
            "confidence": confidence,
            "intent": intent,
            "handoff": handoff,
            "sources": sources,
            "chunks_used": len(chunks),
        }

    # -------------------------------------------------------------------------
    # Step 4: Confidence Scoring
    # -------------------------------------------------------------------------

    async def score_confidence(self, answer: str, chunks: list[dict]) -> float:
        """
        Extract or estimate a confidence score for the generated answer.

        The LLM is instructed to include a "[Confidence: X/10]" tag in its
        response. This method tries to parse that tag first. If it's not found
        (the LLM didn't follow instructions), we fall back to a heuristic:

        - If relevant chunks were found: assume moderate confidence (0.7).
        - If no chunks were found: assume low confidence (0.3), since the
          answer is probably not grounded in real knowledge.

        Args:
            answer: The full text of the LLM's response.
            chunks: The RAG chunks that were provided as context (used for
                    the heuristic fallback).

        Returns:
            A float between 0.0 and 1.0 representing confidence.
            (0.0 = no confidence, 1.0 = fully confident)
        """
        import re

        # Try to extract the self-reported confidence from the answer text
        # Looks for patterns like "[Confidence: 8/10]"
        match = re.search(r"\[Confidence:\s*(\d+)/10\]", answer)
        if match:
            # Convert from 1-10 scale to 0.0-1.0 scale
            return float(match.group(1)) / 10.0

        # Heuristic fallback: if we had relevant chunks, the answer is probably decent
        if chunks and len(chunks) > 0:
            return 0.7
        # No chunks means the LLM was guessing -- low confidence
        return 0.3

    # -------------------------------------------------------------------------
    # Step 5: Handoff Decision
    # -------------------------------------------------------------------------

    async def should_handoff(
        self, confidence: float, intent: str, rules: list[str]
    ) -> bool:
        """
        Determine if the conversation should be escalated to a human agent.

        This is a rule-based decision (not LLM-based) for speed and predictability.
        The logic is intentionally conservative -- it's better to escalate
        unnecessarily than to give a customer a bad answer.

        Decision rules:
        1. If confidence is below 0.5 (50%), ALWAYS hand off. The AI is not
           confident enough to help.
        2. If the intent is "Complaint" AND confidence is below 0.7 (70%),
           hand off. Complaints are sensitive -- customers who are already
           frustrated should talk to a human unless we're very confident
           we can help.
        3. Otherwise, let the AI continue handling the conversation.

        Args:
            confidence: The confidence score (0.0 to 1.0) from score_confidence().
            intent: The classified intent (e.g., "FAQ", "Complaint").
            rules: Custom rules from bot config (reserved for future use --
                   could add custom handoff triggers).

        Returns:
            True if the conversation should be handed off to a human, False otherwise.
        """
        # Rule 1: Low confidence always triggers handoff
        if confidence < 0.5:
            return True
        # Rule 2: Complaints with moderate confidence also trigger handoff
        if intent == "Complaint" and confidence < 0.7:
            return True
        # Otherwise, the AI continues handling it
        return False

    # -------------------------------------------------------------------------
    # Bonus: Suggested reply for human agents
    # -------------------------------------------------------------------------

    async def get_suggested_reply(
        self,
        conversation_history: list[dict],
        bot_config: dict,
    ) -> str:
        """
        Generate a suggested reply for a human agent to send.

        When a conversation has been escalated to a human, this method helps
        the agent by drafting a suggested response based on the conversation
        history. The agent can then edit and send it, saving time.

        This is an "AI copilot" feature -- the human is still in control,
        but the AI helps them work faster.

        Args:
            conversation_history: The full conversation so far (list of
                                  dicts with "role" and "content").
            bot_config: Bot configuration (used to get the bot name for
                        the prompt).

        Returns:
            A suggested reply string that the human agent can edit and send.
        """
        bot_name = bot_config.get("name", "Assistant")

        # Format recent history (last 10 messages) for the prompt
        history_text = ""
        for msg in conversation_history[-10:]:
            role = msg.get("role", "customer")
            content = msg.get("content", "")
            history_text += f"{role}: {content}\n"

        system_prompt = f"""You are helping a human support agent for {bot_name}.
Based on the conversation history, suggest a helpful reply the agent could send.
Be concise and professional. Write only the suggested reply, nothing else."""

        return await self.llm.chat(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": f"Conversation:\n{history_text}\n\nSuggest a reply:"}],
            temperature=0.3,
        )
