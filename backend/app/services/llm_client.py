"""
LLM Client Service
===================

This module provides a unified interface for communicating with different Large
Language Model (LLM) providers. Instead of scattering API-specific code throughout
the codebase, every part of the application talks to this single client.

Why it exists:
- BotForge supports multiple LLM backends: Anthropic Claude, OpenAI GPT, and
  local Ollama models. This client abstracts away the differences so that the
  rest of the code can simply call `llm.chat(...)` without caring which provider
  is active.
- Switching providers is a one-line config change (`llm_provider` in settings).

How it fits in the architecture:
- Used by **ai_engine.py** for intent classification, answer generation, and
  suggested replies.
- Used by **image_processor.py** (via the `vision` method) to describe images.
- Could be used by any future service that needs LLM capabilities.

Supported capabilities:
1. **chat()** - Send a conversation (system prompt + messages) to the LLM and
   get a text response back.
2. **embed()** - Generate a vector embedding for a piece of text (used for
   semantic search in the RAG pipeline).
3. **vision()** - Send an image + text prompt to Claude Vision and get a
   description back.
"""

import json
from typing import AsyncIterator

import httpx
from app.config import get_settings


class LLMClient:
    """
    Abstraction over Claude, OpenAI, and Ollama LLM providers.

    This class acts as a "router" for LLM calls. You create an instance,
    and it reads which provider to use from the application settings
    (or you can override it in the constructor). Then every call to
    `chat()` is forwarded to the correct provider-specific method.

    Attributes:
        provider (str): Which LLM backend to use ("claude", "openai", or "ollama").
        settings: The application settings object containing API keys and URLs.
    """

    def __init__(self, provider: str | None = None):
        """
        Initialize the LLM client.

        Args:
            provider: Optionally override the default provider from settings.
                      If None, uses the value from app config (e.g., "claude").
        """
        settings = get_settings()
        self.provider = provider or settings.llm_provider
        self.settings = settings

    def _openai_client(self):
        """
        Build an AsyncOpenAI client, honoring an optional custom base_url.

        When `openai_base_url` is blank the SDK talks to real OpenAI. When it's
        set, the exact same code path talks to any OpenAI-compatible endpoint
        (Groq, OpenRouter, Together, self-hosted vLLM, ...). This is what lets a
        deployment serve free open-source models without changing any logic.
        """
        from openai import AsyncOpenAI

        kwargs = {"api_key": self.settings.openai_api_key}
        if self.settings.openai_base_url:
            kwargs["base_url"] = self.settings.openai_base_url
        return AsyncOpenAI(**kwargs)

    # -------------------------------------------------------------------------
    # Main public method: chat
    # -------------------------------------------------------------------------

    async def chat(
        self,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str:
        """
        Send a chat request to the configured LLM provider and return the response text.

        This is the primary method used throughout BotForge. It accepts a system
        prompt (instructions for the LLM) and a list of conversation messages,
        then delegates to the appropriate provider-specific method.

        Args:
            system_prompt: Instructions that tell the LLM how to behave (e.g.,
                           "You are a friendly customer support assistant").
            messages: A list of message dicts, each with "role" and "content" keys.
                      Example: [{"role": "user", "content": "What are your hours?"}]
            temperature: Controls randomness of the response. Lower values (0.1)
                         make the output more focused/deterministic; higher values
                         (0.9) make it more creative. Default is 0.3 for consistency.
            max_tokens: Maximum number of tokens (roughly words) in the response.

        Returns:
            The LLM's response as a plain string.

        Raises:
            ValueError: If the configured provider is not recognized.
        """
        if self.provider == "claude":
            return await self._chat_claude(system_prompt, messages, temperature, max_tokens)
        elif self.provider == "openai":
            return await self._chat_openai(system_prompt, messages, temperature, max_tokens)
        elif self.provider == "ollama":
            return await self._chat_ollama(system_prompt, messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    # -------------------------------------------------------------------------
    # Streaming chat (token-by-token)
    # -------------------------------------------------------------------------

    async def chat_stream(
        self,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncIterator[str]:
        """
        Stream a chat response token-by-token from the configured provider.

        Yields successive text deltas as they arrive from the model. Used by
        the SSE streaming endpoint so the widget can render the answer as it
        is generated (typing-cursor effect) instead of waiting for the full
        response.

        Yields:
            str: Each yielded value is the next piece of text from the model.
        """
        if self.provider == "claude":
            agen = self._stream_claude(system_prompt, messages, temperature, max_tokens)
        elif self.provider == "openai":
            agen = self._stream_openai(system_prompt, messages, temperature, max_tokens)
        elif self.provider == "ollama":
            agen = self._stream_ollama(system_prompt, messages, temperature, max_tokens)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")
        async for chunk in agen:
            yield chunk

    async def _stream_claude(
        self, system_prompt: str, messages: list[dict], temperature: float, max_tokens: int
    ) -> AsyncIterator[str]:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.settings.claude_api_key)
        async with client.messages.stream(
            model=self.settings.claude_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    async def _stream_openai(
        self, system_prompt: str, messages: list[dict], temperature: float, max_tokens: int
    ) -> AsyncIterator[str]:
        client = self._openai_client()
        all_messages = [{"role": "system", "content": system_prompt}] + messages
        stream = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=all_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta

    async def _stream_ollama(
        self, system_prompt: str, messages: list[dict], temperature: float, max_tokens: int
    ) -> AsyncIterator[str]:
        all_messages = [{"role": "system", "content": system_prompt}] + messages
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self.settings.ollama_base_url}/api/chat",
                json={
                    "model": self.settings.ollama_model,
                    "messages": all_messages,
                    "stream": True,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    delta = data.get("message", {}).get("content")
                    if delta:
                        yield delta
                    if data.get("done"):
                        break

    # -------------------------------------------------------------------------
    # Provider-specific chat implementations
    # -------------------------------------------------------------------------

    async def _chat_claude(
        self, system_prompt: str, messages: list[dict], temperature: float, max_tokens: int
    ) -> str:
        """
        Send a chat request to Anthropic's Claude API.

        Claude treats the system prompt separately from the messages (unlike
        OpenAI where it's just another message with role "system"). We use
        the official `anthropic` Python SDK with async support.

        Data flow:
        1. Create an async Anthropic client with the API key from settings.
        2. Call messages.create() with the model, system prompt, and messages.
        3. Extract and return the text from the first content block of the response.

        Returns:
            The assistant's reply as a string.
        """
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.settings.claude_api_key)
        response = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text

    async def _chat_openai(
        self, system_prompt: str, messages: list[dict], temperature: float, max_tokens: int
    ) -> str:
        """
        Send a chat request to OpenAI's GPT API.

        OpenAI's chat API expects the system prompt as a message with role "system"
        prepended to the conversation. We merge it into the messages list before
        sending.

        Data flow:
        1. Prepend the system prompt as a system-role message.
        2. Create an async OpenAI client with the API key from settings.
        3. Call chat.completions.create() with the combined messages.
        4. Extract and return the text from the first choice's message.

        Returns:
            The assistant's reply as a string.
        """
        client = self._openai_client()
        # OpenAI expects the system prompt as the first message in the list
        all_messages = [{"role": "system", "content": system_prompt}] + messages
        response = await client.chat.completions.create(
            model=self.settings.openai_model,
            messages=all_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # content is None when the model returns only tool calls; default to ""
        return response.choices[0].message.content or ""

    async def _chat_ollama(
        self, system_prompt: str, messages: list[dict], temperature: float, max_tokens: int
    ) -> str:
        """
        Send a chat request to a locally running Ollama instance.

        Ollama provides a REST API for locally hosted open-source models (e.g.,
        Llama 3.1). This is useful for development or when you want to avoid
        sending data to external APIs.

        Data flow:
        1. Prepend the system prompt as a system-role message (same as OpenAI).
        2. POST to the Ollama /api/chat endpoint with the model name and messages.
        3. Parse the JSON response and extract the assistant's message content.

        Note: stream=False so we get the full response in one shot (not streamed).
        The timeout is 120 seconds since local models can be slower.

        Returns:
            The assistant's reply as a string.
        """
        # Ollama uses the same message format as OpenAI (system role as a message)
        all_messages = [{"role": "system", "content": system_prompt}] + messages
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.settings.ollama_base_url}/api/chat",
                json={
                    "model": self.settings.ollama_model,
                    "messages": all_messages,
                    "stream": False,  # Get full response at once, not token by token
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
                timeout=120.0,  # Local models can be slow, especially on CPU
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

    # -------------------------------------------------------------------------
    # Agent loop with tool use
    # -------------------------------------------------------------------------

    async def run_agent(
        self,
        system_prompt: str,
        user_message: str,
        tools: list,             # list[app.services.tools.Tool]
        max_iterations: int = 5,
    ) -> dict:
        """
        Run a tool-using agent loop until the model produces a final text answer
        or `max_iterations` is reached.

        The model can call any of the supplied tools. We execute each call,
        feed the result back, and keep going. Each provider needs its own
        message-format dance, so we route to a private helper per provider.

        Returns:
            {
              "answer": str,                # final assistant text
              "tool_calls": [               # full audit trail
                  {"name": str, "input": dict, "result": str},
                  ...
              ],
              "iterations": int,
            }
        """
        if self.provider == "claude":
            return await self._agent_claude(system_prompt, user_message, tools, max_iterations)
        elif self.provider == "openai":
            return await self._agent_openai(system_prompt, user_message, tools, max_iterations)
        elif self.provider == "ollama":
            return await self._agent_ollama(system_prompt, user_message, tools, max_iterations)
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    async def _agent_claude(self, system_prompt, user_message, tools, max_iterations) -> dict:
        """Anthropic Claude tool-use loop."""
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.settings.claude_api_key)

        tool_defs = [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in tools
        ]
        tools_by_name = {t.name: t for t in tools}

        messages: list[dict] = [{"role": "user", "content": user_message}]
        trace: list[dict] = []

        for i in range(max_iterations):
            response = await client.messages.create(
                model=self.settings.claude_model,
                max_tokens=1024,
                system=system_prompt,
                tools=tool_defs,
                messages=messages,
            )

            # Always echo the assistant's full content (text + tool_use blocks) back
            # into history — Claude requires this when the next turn is tool_result.
            messages.append({"role": "assistant", "content": response.content})

            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if not tool_uses:
                # Final text answer.
                text = "".join(b.text for b in response.content if b.type == "text")
                return {"answer": text, "tool_calls": trace, "iterations": i + 1}

            # Execute every tool the model wanted, send results back as one user turn.
            tool_results = []
            for tu in tool_uses:
                handler = tools_by_name.get(tu.name)
                try:
                    result = await handler.handler(tu.input) if handler else f"Unknown tool: {tu.name}"
                except Exception as e:  # tool errors must not break the loop
                    result = f"Error calling {tu.name}: {e}"
                trace.append({"name": tu.name, "input": tu.input, "result": result})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": result,
                })
            messages.append({"role": "user", "content": tool_results})

        return {
            "answer": "I'm having trouble completing this — let me connect you to a human.",
            "tool_calls": trace,
            "iterations": max_iterations,
        }

    async def _agent_openai(self, system_prompt, user_message, tools, max_iterations) -> dict:
        """OpenAI function-calling loop."""
        import json as _json

        client = self._openai_client()

        tool_defs = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]
        tools_by_name = {t.name: t for t in tools}

        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        trace: list[dict] = []

        for i in range(max_iterations):
            response = await client.chat.completions.create(
                model=self.settings.openai_model,
                messages=messages,
                tools=tool_defs,
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                return {"answer": msg.content or "", "tool_calls": trace, "iterations": i + 1}

            # Append the assistant's tool-call message verbatim — required so the
            # follow-up `role: tool` messages have a tool_call_id to match against.
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })

            for tc in msg.tool_calls:
                try:
                    args = _json.loads(tc.function.arguments) if tc.function.arguments else {}
                except Exception:
                    args = {}
                handler = tools_by_name.get(tc.function.name)
                try:
                    result = await handler.handler(args) if handler else f"Unknown tool: {tc.function.name}"
                except Exception as e:
                    result = f"Error calling {tc.function.name}: {e}"
                trace.append({"name": tc.function.name, "input": args, "result": result})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

        return {
            "answer": "I couldn't complete this — please hold while I escalate.",
            "tool_calls": trace,
            "iterations": max_iterations,
        }

    async def _agent_ollama(self, system_prompt, user_message, tools, max_iterations) -> dict:
        """
        Ollama tool-use loop. Requires a tool-capable model — llama3.1+,
        qwen2.5+, or mistral-nemo. Older models will simply never emit
        `tool_calls` and the loop will return their first text answer.
        """
        import json as _json

        tool_defs = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.input_schema,
                },
            }
            for t in tools
        ]
        tools_by_name = {t.name: t for t in tools}

        messages: list[dict] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        trace: list[dict] = []

        async with httpx.AsyncClient(timeout=180.0) as client:
            for i in range(max_iterations):
                response = await client.post(
                    f"{self.settings.ollama_base_url}/api/chat",
                    json={
                        "model": self.settings.ollama_model,
                        "messages": messages,
                        "tools": tool_defs,
                        "stream": False,
                    },
                )
                response.raise_for_status()
                msg = response.json()["message"]

                tool_calls = msg.get("tool_calls") or []
                if not tool_calls:
                    return {
                        "answer": msg.get("content", ""),
                        "tool_calls": trace,
                        "iterations": i + 1,
                    }

                messages.append(msg)

                for tc in tool_calls:
                    fn = tc.get("function", {})
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = _json.loads(args)
                        except Exception:
                            args = {}
                    name = fn.get("name", "")
                    handler = tools_by_name.get(name)
                    try:
                        result = await handler.handler(args) if handler else f"Unknown tool: {name}"
                    except Exception as e:
                        result = f"Error calling {name}: {e}"
                    trace.append({"name": name, "input": args, "result": result})
                    messages.append({"role": "tool", "content": result})

        return {
            "answer": "I couldn't complete this — let me get a human.",
            "tool_calls": trace,
            "iterations": max_iterations,
        }

    # -------------------------------------------------------------------------
    # Embedding generation
    # -------------------------------------------------------------------------

    async def embed(self, text: str) -> list[float]:
        """
        Generate a vector embedding for a piece of text.

        Embeddings are numerical representations of text that capture semantic
        meaning. Two pieces of text with similar meanings will have similar
        embeddings (close together in vector space). This is the foundation
        of the RAG pipeline's semantic search.

        Uses the sentence-transformers library with the "all-MiniLM-L6-v2" model,
        which runs locally (no API call needed). This model produces 384-dimensional
        vectors and is fast enough for real-time use.

        Args:
            text: The text to embed (a question, a document chunk, etc.).

        Returns:
            A list of floats representing the embedding vector (384 dimensions).
        """
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(self.settings.embedding_model)
        embedding = model.encode(text)
        return embedding.tolist()

    # -------------------------------------------------------------------------
    # Vision (image understanding)
    # -------------------------------------------------------------------------

    async def vision(self, image_bytes: bytes, prompt: str) -> str:
        """
        Describe an image using the configured provider's vision model.

        Routes to:
        - "claude"  -> Anthropic Claude Vision
        - "openai"  -> GPT-4o (or whatever `openai_vision_model` is set to)
        - "ollama"  -> Local Ollama vision model (e.g. "llava", "llama3.2-vision")

        Args:
            image_bytes: Raw bytes of the image (JPEG/PNG).
            prompt: Instructions for what to focus on.

        Returns:
            A text description of the image content.
        """
        if self.provider == "claude":
            return await self._vision_claude(image_bytes, prompt)
        elif self.provider == "openai":
            return await self._vision_openai(image_bytes, prompt)
        elif self.provider == "ollama":
            return await self._vision_ollama(image_bytes, prompt)
        else:
            raise ValueError(f"Unknown LLM provider for vision: {self.provider}")

    async def _vision_claude(self, image_bytes: bytes, prompt: str) -> str:
        import anthropic
        import base64

        client = anthropic.AsyncAnthropic(api_key=self.settings.claude_api_key)
        b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = await client.messages.create(
            model=self.settings.claude_vision_model,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": b64_image,
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )
        return response.content[0].text

    async def _vision_openai(self, image_bytes: bytes, prompt: str) -> str:
        """OpenAI Vision via Chat Completions (image_url with base64 data URI)."""
        import base64

        client = self._openai_client()
        b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")
        response = await client.chat.completions.create(
            model=self.settings.openai_vision_model,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"},
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content

    async def _vision_ollama(self, image_bytes: bytes, prompt: str) -> str:
        """
        Ollama vision via /api/chat. The model must be a multimodal one
        (e.g. `llava`, `llama3.2-vision`, `bakllava`). Pulled with:
            ollama pull llava
        """
        import base64

        b64_image = base64.standard_b64encode(image_bytes).decode("utf-8")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.settings.ollama_base_url}/api/chat",
                json={
                    "model": self.settings.ollama_vision_model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt,
                            "images": [b64_image],
                        }
                    ],
                    "stream": False,
                    "options": {"num_predict": 512},
                },
                timeout=180.0,  # vision models on CPU can be slow
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
