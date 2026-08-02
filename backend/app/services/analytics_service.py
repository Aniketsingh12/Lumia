"""
Analytics Service
==================

This module computes analytics and reporting data from conversation and message
records stored in Supabase. It powers the analytics dashboard that bot owners
use to understand how their bot is performing.

Why it exists:
- Bot owners need to know: How many conversations are happening? Is the AI
  resolving them or are they being escalated? What are customers asking about?
  Which channels are most popular? What questions is the AI struggling with?
- This service crunches the raw data and returns structured analytics objects
  that the frontend can render into charts and tables.

How it fits in the architecture:
- Called by the **analytics API routes** when a bot owner views their dashboard.
- Reads from the same Supabase tables that **conversation_manager.py** writes to.
- Returns Pydantic model objects (defined in app/models/analytics.py) for
  type-safe, well-structured API responses.

Key metrics computed:
- **Overview stats**: Total messages, conversations, AI resolution rate, handoffs,
  satisfaction scores.
- **Top questions**: Most frequently asked questions by customers.
- **Unanswered questions**: Questions where the AI had low confidence (gaps in
  the knowledge base).
- **Channel breakdown**: Distribution of conversations across platforms
  (WhatsApp, Slack, Instagram, website).
"""

from datetime import datetime, timedelta, timezone

from app.database import get_supabase
from app.models.analytics import (
    OverviewStats,
    TopQuestion,
    ChannelBreakdown,
    UnansweredQuestion,
    AnalyticsResponse,
)


class AnalyticsService:
    """
    Compute analytics from conversation and message data stored in Supabase.

    This service queries the database, aggregates the results, and returns
    structured analytics objects. It's designed to be called from API routes
    and return data ready for the frontend dashboard.

    Attributes:
        db: The Supabase client used for all database queries.
    """

    def __init__(self):
        """Initialize with a Supabase database client."""
        self.db = get_supabase()

    # -------------------------------------------------------------------------
    # Helper: Date range calculation
    # -------------------------------------------------------------------------

    def _get_date_range(self, range_str: str) -> tuple[datetime, datetime]:
        """
        Convert a human-friendly date range string into start/end datetimes.

        Supports common dashboard time ranges. The end is always "now" and
        the start is calculated by subtracting the specified number of days.

        Args:
            range_str: One of "1d" (last day), "7d" (last week), "30d" (last
                       month), or "90d" (last quarter). Defaults to 7d if
                       the string is not recognized.

        Returns:
            A tuple of (start_datetime, end_datetime) in UTC.
        """
        end = datetime.now(timezone.utc)
        days_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
        days = days_map.get(range_str, 7)  # Default to 7 days if unrecognized
        start = end - timedelta(days=days)
        return start, end

    # -------------------------------------------------------------------------
    # Overview statistics
    # -------------------------------------------------------------------------

    async def get_overview(self, bot_id: str, date_range: str = "7d") -> OverviewStats:
        """
        Get high-level overview statistics for a bot within a date range.

        This is the main "at a glance" view that appears at the top of the
        analytics dashboard. It answers: "How is my bot doing overall?"

        Metrics computed:
        - total_messages: How many messages were exchanged in this period.
        - total_conversations: How many conversations started in this period.
        - ai_resolution_rate: What percentage of conversations the AI resolved
          without human intervention (0.0 to 1.0).
        - avg_response_time: Average time to first response (currently a
          placeholder value of 1.2 seconds).
        - human_handoffs: How many conversations were escalated to humans.
        - satisfaction_score: Average customer satisfaction rating (from
          conversations that have a satisfaction_score set).

        Args:
            bot_id: The bot to get statistics for.
            date_range: Time window ("1d", "7d", "30d", or "90d").

        Returns:
            An OverviewStats model with all computed metrics.
        """
        start, end = self._get_date_range(date_range)
        start_iso = start.isoformat()

        # Query 1: Count total messages in the date range
        messages = (
            self.db.table("messages")
            .select("id", count="exact")
            .eq("conversation_id.bot_id", bot_id)
            .gte("created_at", start_iso)
            .execute()
        )

        # Query 2: Get all conversations in the date range (we need the full
        # records to compute multiple metrics from them)
        conversations = (
            self.db.table("conversations")
            .select("*")
            .eq("bot_id", bot_id)
            .gte("started_at", start_iso)
            .execute()
        )

        # Process conversation data to compute various metrics
        conv_list = conversations.data or []
        total_convos = len(conv_list)

        # Filter conversations by status/resolution type
        resolved = [c for c in conv_list if c.get("status") == "resolved"]
        ai_resolved = [c for c in conv_list if c.get("ai_resolution")]
        escalated = [c for c in conv_list if c.get("status") == "escalated"]

        # AI resolution rate = conversations resolved by AI / total conversations
        ai_rate = len(ai_resolved) / total_convos if total_convos > 0 else 0

        # Average satisfaction from conversations that have a score
        satisfaction_scores = [
            c["satisfaction_score"]
            for c in conv_list
            if c.get("satisfaction_score") is not None
        ]
        avg_satisfaction = (
            sum(satisfaction_scores) / len(satisfaction_scores) if satisfaction_scores else 0
        )

        return OverviewStats(
            total_messages=messages.count or 0,
            total_conversations=total_convos,
            ai_resolution_rate=round(ai_rate, 2),
            avg_response_time=1.2,  # TODO: Calculate from actual message timestamps
            human_handoffs=len(escalated),
            satisfaction_score=round(avg_satisfaction, 1),
        )

    # -------------------------------------------------------------------------
    # Top questions
    # -------------------------------------------------------------------------

    async def get_top_questions(self, bot_id: str, limit: int = 10) -> list[TopQuestion]:
        """
        Get the most frequently asked questions by customers.

        This helps bot owners understand what their customers care about most.
        It can also highlight areas where the knowledge base should be expanded.

        How it works:
        1. Fetch the last 500 customer messages from the database.
        2. Normalize each message (lowercase, strip punctuation).
        3. Count how many times each unique message appears.
        4. Return the top N most frequent questions.

        Note: This is a simple exact-match frequency count. Messages that are
        phrased differently but ask the same thing (e.g., "What are your hours?"
        vs "When are you open?") are counted separately. A future improvement
        could use embeddings to cluster similar questions.

        Args:
            bot_id: The bot to analyze (currently not filtered -- see TODO).
            limit: Maximum number of top questions to return (default 10).

        Returns:
            A list of TopQuestion objects, each with the question text and count,
            sorted by frequency descending.
        """
        # Fetch recent customer messages (limited to 500 to avoid huge queries)
        messages = (
            self.db.table("messages")
            .select("content")
            .eq("role", "customer")
            .limit(500)
            .execute()
        )

        # Count frequency of each unique (normalized) message
        question_counts: dict[str, int] = {}
        for msg in messages.data or []:
            content = msg.get("content", "").strip()
            if content and len(content) > 10:  # Ignore very short messages (greetings, etc.)
                # Normalize: lowercase and strip trailing punctuation
                normalized = content.lower().rstrip("?!. ")
                question_counts[normalized] = question_counts.get(normalized, 0) + 1

        # Sort by count descending and take the top N
        sorted_questions = sorted(question_counts.items(), key=lambda x: x[1], reverse=True)

        return [
            TopQuestion(question=q, count=c) for q, c in sorted_questions[:limit]
        ]

    # -------------------------------------------------------------------------
    # Unanswered / low-confidence questions
    # -------------------------------------------------------------------------

    async def get_unanswered(self, bot_id: str) -> list[UnansweredQuestion]:
        """
        Get questions where the AI had low confidence in its answer.

        These represent gaps in the bot's knowledge base -- questions that
        customers are asking but the bot cannot answer well. Bot owners should
        review these and add relevant documents to improve the bot.

        How it works:
        1. Query AI messages that have a confidence_score below 0.5 (50%).
        2. Group and count duplicate low-confidence responses.
        3. Sort by frequency so the most common gaps appear first.

        Args:
            bot_id: The bot to analyze (currently not filtered -- see TODO).

        Returns:
            A list of UnansweredQuestion objects, each with the question text,
            count of occurrences, and when it was first asked.
        """
        # Fetch AI responses with low confidence scores
        messages = (
            self.db.table("messages")
            .select("content, confidence_score, created_at")
            .eq("role", "ai")
            .lt("confidence_score", 0.5)  # Below 50% confidence
            .limit(100)
            .execute()
        )

        # Group by content (truncated to 100 chars) and count occurrences
        unanswered: dict[str, dict] = {}
        for msg in messages.data or []:
            content = msg.get("content", "")[:100]  # Truncate for grouping
            if content in unanswered:
                unanswered[content]["count"] += 1
            else:
                unanswered[content] = {
                    "question": content,
                    "count": 1,
                    "first_asked": msg.get("created_at"),
                }

        # Sort by count descending (most common gaps first)
        return [
            UnansweredQuestion(**data)
            for data in sorted(unanswered.values(), key=lambda x: x["count"], reverse=True)
        ]

    # -------------------------------------------------------------------------
    # Channel breakdown
    # -------------------------------------------------------------------------

    async def get_channel_breakdown(self, bot_id: str) -> list[ChannelBreakdown]:
        """
        Get the distribution of conversations across messaging channels.

        Shows how customers are reaching the bot -- via WhatsApp, Slack,
        Instagram, or the website. This helps bot owners understand which
        channels to prioritize and where to focus integration efforts.

        Args:
            bot_id: The bot to analyze.

        Returns:
            A list of ChannelBreakdown objects, each with the channel name,
            conversation count, and percentage of total. Sorted by count
            descending (most popular channel first).
        """
        # Fetch just the channel field for all conversations for this bot
        conversations = (
            self.db.table("conversations")
            .select("channel")
            .eq("bot_id", bot_id)
            .execute()
        )

        # Count conversations per channel
        channel_counts: dict[str, int] = {}
        for conv in conversations.data or []:
            ch = conv.get("channel", "website")  # Default to "website" if missing
            channel_counts[ch] = channel_counts.get(ch, 0) + 1

        # Calculate percentages (avoid division by zero with `or 1`)
        total = sum(channel_counts.values()) or 1
        return [
            ChannelBreakdown(
                channel=ch,
                count=count,
                percentage=round(count / total * 100, 1),
            )
            for ch, count in sorted(channel_counts.items(), key=lambda x: x[1], reverse=True)
        ]

    # -------------------------------------------------------------------------
    # Full analytics bundle
    # -------------------------------------------------------------------------

    async def get_full_analytics(self, bot_id: str, date_range: str = "7d") -> AnalyticsResponse:
        """
        Get all analytics data in a single call.

        This is a convenience method that calls all the individual analytics
        methods and bundles the results into one AnalyticsResponse. It's used
        by the frontend dashboard to load all analytics data at once instead
        of making multiple API calls.

        Args:
            bot_id: The bot to get analytics for.
            date_range: Time window for the overview stats ("1d", "7d", "30d", "90d").

        Returns:
            An AnalyticsResponse containing overview stats, top questions,
            unanswered questions, and channel breakdown -- everything needed
            to render the analytics dashboard.
        """
        overview = await self.get_overview(bot_id, date_range)
        top_questions = await self.get_top_questions(bot_id)
        unanswered = await self.get_unanswered(bot_id)
        channel_breakdown = await self.get_channel_breakdown(bot_id)

        return AnalyticsResponse(
            overview=overview,
            top_questions=top_questions,
            unanswered=unanswered,
            channel_breakdown=channel_breakdown,
        )
