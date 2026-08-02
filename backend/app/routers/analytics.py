"""
Analytics Router
=================

This router provides analytics and reporting endpoints for the BotForge dashboard.
It gives bot owners and agents insight into how their bots are performing, what
customers are asking about, and where the bots need improvement.

Endpoints provided:
    GET /overview        - High-level performance stats (message count, response time, etc.)
    GET /top-questions   - Most frequently asked questions
    GET /unanswered      - Questions the bot could not answer (low confidence / handoff)
    GET /channels        - Message volume breakdown by channel (web, WhatsApp, Slack, etc.)
    GET /satisfaction    - Customer satisfaction score over a time range
    GET /export          - Export full analytics data (for download or external reporting)

All endpoints require authentication and take a bot_id query parameter to scope
the analytics to a specific bot. Most also accept a time range parameter.

All data computation is delegated to the AnalyticsService, which queries the
database and computes aggregated metrics. The router simply validates inputs,
calls the service, and returns the results.

Design Decisions:
    - Analytics are always scoped to a single bot (via required bot_id parameter).
    - Time range is specified as a string like "7d" (7 days), "30d" (30 days), etc.
    - The export endpoint returns the same JSON format regardless of the "format"
      parameter (CSV/PDF export could be added later).
"""

from fastapi import APIRouter, Depends, Query

from app.services.analytics_service import AnalyticsService
from app.models.analytics import AnalyticsResponse, OverviewStats, TopQuestion, ChannelBreakdown
from app.middleware.auth import get_current_user

# Create the router instance. Mounted with prefix like "/api/analytics".
router = APIRouter()


@router.get("/overview", response_model=OverviewStats)
async def get_overview(
    bot_id: str = Query(...),
    range: str = Query("7d"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get high-level overview statistics for a bot.

    HTTP Method: GET
    URL: /overview?bot_id=<uuid>&range=<time_range>
    Auth Required: Yes

    Query Parameters:
        - bot_id (str, required): The UUID of the bot to get stats for
        - range (str, optional): Time range for the stats. Defaults to "7d" (7 days).
          Examples: "1d", "7d", "30d", "90d"

    Request Flow:
        1. Instantiate the AnalyticsService.
        2. Call get_overview() which queries the database to compute:
           - Total messages received in the time range
           - Total conversations started
           - Average AI response time
           - Handoff rate (percentage of conversations escalated to humans)
           - Customer satisfaction score (from feedback data)
        3. Return the computed stats.

    Response (OverviewStats):
        - total_messages (int), total_conversations (int)
        - avg_response_time (float), handoff_rate (float)
        - satisfaction_score (float)
    """
    service = AnalyticsService()
    return await service.get_overview(bot_id, range)


@router.get("/top-questions", response_model=list[TopQuestion])
async def get_top_questions(
    bot_id: str = Query(...),
    limit: int = Query(10),
    current_user: dict = Depends(get_current_user),
):
    """
    Get the most frequently asked questions for a bot.

    HTTP Method: GET
    URL: /top-questions?bot_id=<uuid>&limit=<number>
    Auth Required: Yes

    Query Parameters:
        - bot_id (str, required): The UUID of the bot
        - limit (int, optional): Maximum number of questions to return. Defaults to 10.

    Request Flow:
        1. Call the AnalyticsService which analyzes customer messages to identify
           the most common questions or intents.
        2. Return the top N questions sorted by frequency.

    This helps bot owners understand what customers ask about most, so they can
    prioritize adding knowledge base content for those topics.

    Response: List of TopQuestion objects, each containing:
        - question (str): The question text or intent category
        - count (int): How many times this question was asked
        - avg_confidence (float): Average AI confidence when answering this question
    """
    service = AnalyticsService()
    return await service.get_top_questions(bot_id, limit)


@router.get("/unanswered")
async def get_unanswered(
    bot_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Get questions the bot could not answer confidently.

    HTTP Method: GET
    URL: /unanswered?bot_id=<uuid>
    Auth Required: Yes

    Query Parameters:
        - bot_id (str, required): The UUID of the bot

    Request Flow:
        1. Call the AnalyticsService which finds messages where the bot's confidence
           was below the threshold or where a handoff occurred.
        2. Return these "unanswered" questions.

    This is a key improvement tool: it shows bot owners exactly what knowledge gaps
    exist in their bot's training data, so they can upload relevant documents or
    add custom rules to address those questions.

    Response: List of unanswered question objects (format depends on AnalyticsService).
    """
    service = AnalyticsService()
    return await service.get_unanswered(bot_id)


@router.get("/channels", response_model=list[ChannelBreakdown])
async def get_channel_breakdown(
    bot_id: str = Query(...),
    current_user: dict = Depends(get_current_user),
):
    """
    Get message volume breakdown by communication channel.

    HTTP Method: GET
    URL: /channels?bot_id=<uuid>
    Auth Required: Yes

    Query Parameters:
        - bot_id (str, required): The UUID of the bot

    Request Flow:
        1. Call the AnalyticsService which groups conversations/messages by channel
           (web, whatsapp, instagram, slack, email) and counts them.
        2. Return the breakdown.

    This helps bot owners understand which channels are most popular and where to
    focus their integration efforts.

    Response: List of ChannelBreakdown objects, each containing:
        - channel (str): The channel name (e.g., "web", "whatsapp")
        - message_count (int): Total messages from this channel
        - conversation_count (int): Total conversations from this channel
    """
    service = AnalyticsService()
    return await service.get_channel_breakdown(bot_id)


@router.get("/satisfaction")
async def get_satisfaction(
    bot_id: str = Query(...),
    range: str = Query("7d"),
    current_user: dict = Depends(get_current_user),
):
    """
    Get customer satisfaction score for a bot over a time range.

    HTTP Method: GET
    URL: /satisfaction?bot_id=<uuid>&range=<time_range>
    Auth Required: Yes

    Query Parameters:
        - bot_id (str, required): The UUID of the bot
        - range (str, optional): Time range. Defaults to "7d".

    Request Flow:
        1. Call the overview analytics (which includes satisfaction data).
        2. Extract and return just the satisfaction_score field.

    The satisfaction score is computed from customer feedback (thumbs up/down)
    submitted via the POST /chat/feedback endpoint.

    Response:
        - satisfaction_score (float): Satisfaction percentage (0.0 to 1.0 or 0 to 100)
    """
    # Return satisfaction data over time
    service = AnalyticsService()
    overview = await service.get_overview(bot_id, range)
    return {"satisfaction_score": overview.satisfaction_score}


@router.get("/export")
async def export_analytics(
    bot_id: str = Query(...),
    range: str = Query("7d"),
    format: str = Query("json"),
    current_user: dict = Depends(get_current_user),
):
    """
    Export full analytics data for a bot.

    HTTP Method: GET
    URL: /export?bot_id=<uuid>&range=<time_range>&format=<format>
    Auth Required: Yes

    Query Parameters:
        - bot_id (str, required): The UUID of the bot
        - range (str, optional): Time range. Defaults to "7d".
        - format (str, optional): Export format. Defaults to "json".
          Currently only JSON is supported; CSV/PDF could be added later.

    Request Flow:
        1. Call the AnalyticsService to gather all analytics data for the bot
           within the specified time range.
        2. Return the full analytics payload as JSON.

    This endpoint is used for exporting data to external reporting tools or
    for downloading analytics reports.

    Response: Full analytics data object (format depends on AnalyticsService).
    """
    service = AnalyticsService()
    data = await service.get_full_analytics(bot_id, range)
    return data
