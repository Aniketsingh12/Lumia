"""
Analytics Models - Pydantic schemas for bot performance analytics and reporting.

=== What are Pydantic models? ===
Pydantic models are Python classes that define and validate the shape of data.
When the frontend requests analytics, these models ensure the response has a
consistent, well-structured format that the dashboard charts can rely on.

=== What this file defines ===
This file contains all schemas for the analytics/reporting system:
  - AnalyticsQuery:       Filters for requesting analytics data (bot, date range)
  - OverviewStats:        High-level KPI metrics (messages, resolution rate, etc.)
  - TopQuestion:          A frequently asked question and its count
  - ChannelBreakdown:     Message distribution across channels
  - UnansweredQuestion:   A question the bot couldn't answer
  - AnalyticsResponse:    The complete analytics payload combining all the above

=== How analytics data flows ===
1. User opens the Analytics tab and selects a bot and date range
2. Frontend sends an AnalyticsQuery to the backend
3. Backend queries the database (messages, conversations tables) with aggregations
4. Backend computes metrics and assembles an AnalyticsResponse
5. Frontend renders the data as cards, charts, and tables

=== Why separate sub-models? ===
The analytics response is complex -- it contains different types of data for
different parts of the dashboard. Breaking it into sub-models (OverviewStats,
TopQuestion, etc.) keeps each piece focused and easy to understand, rather
than having one massive flat model with 20+ fields.
"""

from pydantic import BaseModel
from datetime import datetime


class AnalyticsQuery(BaseModel):
    """
    Schema for requesting analytics data with filters.

    Used by: GET /analytics or POST /analytics endpoint
    Sent by: The Analytics tab's filter controls (bot selector, date picker)

    The backend uses these parameters to scope the database queries so only
    relevant data is aggregated and returned.
    """

    # Which bot to show analytics for. Required because all metrics are
    # per-bot -- you wouldn't want to mix data from a sales bot and a support bot.
    bot_id: str

    # Optional explicit start date for the analytics period. If provided,
    # overrides the "range" parameter. Allows the user to pick a custom date range.
    # Expected format: ISO 8601 datetime (e.g., "2026-03-01T00:00:00Z").
    start_date: datetime | None = None

    # Optional explicit end date for the analytics period. If provided,
    # overrides the "range" parameter. Used together with start_date for
    # custom date ranges.
    end_date: datetime | None = None

    # A shorthand for common date ranges, used when start_date/end_date are not set:
    #   - "1d":  Last 24 hours (today's activity)
    #   - "7d":  Last 7 days (default, good weekly overview)
    #   - "30d": Last 30 days (monthly performance review)
    #   - "90d": Last 90 days (quarterly trends)
    # The backend converts this to actual start/end dates before querying.
    range: str = "7d"  # 1d | 7d | 30d | 90d


class OverviewStats(BaseModel):
    """
    High-level key performance indicators (KPIs) displayed as cards at the
    top of the Analytics dashboard.

    Used as: A nested field within AnalyticsResponse
    Rendered as: Big number cards (e.g., "1,234 Total Messages")

    These are the metrics that bot owners check at a glance to understand
    how their bot is performing overall.
    """

    # Total number of messages sent and received across all conversations
    # in the selected time period. Includes customer, AI, and agent messages.
    # Indicates overall usage volume.
    total_messages: int = 0

    # Total number of conversations started in the selected time period.
    # A conversation may contain many messages, so this is typically much
    # smaller than total_messages.
    total_conversations: int = 0

    # Percentage of conversations resolved by the AI without human intervention.
    # Ranges from 0.0 (0%) to 1.0 (100%). This is the most important metric
    # for measuring bot effectiveness -- higher means the AI handles more on its own.
    # Calculated as: conversations where ai_resolution=True / total conversations.
    ai_resolution_rate: float = 0.0

    # Average time in seconds between a customer's message and the AI's response.
    # Lower is better. AI responses are typically near-instant (< 2 seconds),
    # but this metric matters more when human agents are involved, as it
    # reflects the full support team's responsiveness.
    avg_response_time: float = 0.0

    # Number of conversations that were escalated from AI to a human agent.
    # The inverse of AI resolution -- these are conversations the bot couldn't
    # handle alone. A high number suggests the knowledge base needs improvement.
    human_handoffs: int = 0

    # Average customer satisfaction score across all rated conversations.
    # Typically on a 1-5 scale, where 5 is best. Only includes conversations
    # where the customer provided feedback.
    satisfaction_score: float = 0.0


class TopQuestion(BaseModel):
    """
    Represents a frequently asked question detected across conversations.

    Used as: Items in the AnalyticsResponse.top_questions list
    Rendered as: A ranked table of popular questions in the Analytics dashboard

    This helps bot owners understand what their customers ask about most, so
    they can prioritize improving the knowledge base for those topics.
    """

    # The question text, as classified/clustered by the AI intent system.
    # Similar questions are grouped together (e.g., "What's the price?" and
    # "How much does it cost?" might be combined into one entry).
    question: str

    # How many times this question (or similar variations) was asked in the
    # selected time period.
    count: int

    # Whether the bot has a good answer for this question in its knowledge base.
    # True = the bot answered confidently (confidence above threshold).
    # False = the bot struggled or used the fallback message.
    # False items are candidates for knowledge base improvement.
    has_answer: bool = True


class ChannelBreakdown(BaseModel):
    """
    Shows message distribution across different messaging channels.

    Used as: Items in the AnalyticsResponse.channel_breakdown list
    Rendered as: A pie chart or bar chart showing which channels are most popular

    Helps bot owners understand where their customers prefer to communicate,
    so they can prioritize channel integrations and support resources.
    """

    # The channel name (e.g., "website", "whatsapp", "instagram", "slack", "email").
    channel: str

    # The total number of messages sent through this channel in the selected period.
    count: int

    # What percentage of total messages came from this channel.
    # Ranges from 0.0 to 100.0. All channel percentages should sum to 100.
    # Pre-calculated by the backend so the frontend doesn't need to compute it.
    percentage: float


class UnansweredQuestion(BaseModel):
    """
    Represents a question the bot could not answer satisfactorily.

    Used as: Items in the AnalyticsResponse.unanswered list
    Rendered as: A table in the "Knowledge Gaps" section of the Analytics dashboard

    This is one of the most actionable analytics features -- it directly tells
    the bot owner what content they need to add to their knowledge base. Each
    entry is a clear to-do item: "Customers keep asking about X, but the bot
    doesn't know the answer."
    """

    # The unanswered question text, as classified by the AI.
    # Similar unanswered questions are grouped together.
    question: str

    # How many times this question was asked without a satisfactory answer.
    # Higher counts indicate more urgent knowledge gaps to fill.
    count: int

    # When this question was first encountered. Helps bot owners understand
    # whether this is a new gap (recent) or a long-standing one that's been
    # ignored. None if the timestamp wasn't recorded.
    first_asked: datetime | None = None


class AnalyticsResponse(BaseModel):
    """
    The complete analytics payload returned to the frontend.

    Used by: GET /analytics or POST /analytics endpoint (as the response body)
    Sent to: The Analytics tab, which distributes data to various chart components

    This is a composite model that bundles all analytics data into a single
    response. The frontend destructures it and passes each piece to the
    appropriate chart or card component.

    Design decision: We return everything in one API call rather than having
    separate endpoints for each metric. This reduces the number of HTTP requests
    the dashboard needs to make, resulting in a faster page load.
    """

    # High-level KPI metrics displayed as summary cards at the top.
    # Contains totals, rates, and averages for the selected time period.
    overview: OverviewStats = OverviewStats()

    # The most frequently asked questions, ranked by count.
    # Displayed as a table or ranked list in the dashboard.
    top_questions: list[TopQuestion] = []

    # Questions the bot could not answer, representing knowledge base gaps.
    # Displayed in a "Knowledge Gaps" section to guide content improvements.
    unanswered: list[UnansweredQuestion] = []

    # Message distribution across messaging channels (website, WhatsApp, etc.).
    # Displayed as a pie chart or horizontal bar chart.
    channel_breakdown: list[ChannelBreakdown] = []

    # Time-series data for message volume over the selected period.
    # Each dict typically contains {"date": "2026-03-15", "count": 42}.
    # Displayed as a line chart or area chart showing activity trends.
    # Using a generic list[dict] keeps this flexible for different time
    # granularities (hourly, daily, weekly).
    messages_over_time: list[dict] = []

    # Time-series data for customer satisfaction over the selected period.
    # Each dict typically contains {"date": "2026-03-15", "score": 4.2}.
    # Displayed as a line chart showing satisfaction trends over time.
    satisfaction_over_time: list[dict] = []
