"""
Email Channel Router
=====================

This router handles outbound email communication. Unlike the other channel
routers (WhatsApp, Instagram, Slack) which receive incoming messages via webhooks,
the email router currently only supports SENDING replies -- it does not receive
incoming emails.

Endpoints provided:
    POST /reply  - Send an email reply via SMTP

How Email Integration Works:
    - Outbound: When an agent wants to reply to a customer via email, they use
      this endpoint. It connects to an SMTP server and sends the email.
    - Inbound: Not implemented in this router. Inbound email processing would
      typically use a service like SendGrid, Mailgun, or AWS SES with webhook
      forwarding, or an IMAP polling service.

Auth: The /reply endpoint requires JWT authentication because it is called by
human agents from the dashboard, not by an external platform.

Design Decisions:
    - SMTP credentials (host, port, email, password) are stored in application
      settings, not hardcoded.
    - STARTTLS is used for encrypting the SMTP connection.
    - Errors are caught and returned as {"status": "error"} rather than raising
      HTTP exceptions, so the frontend can handle email delivery failures gracefully.
    - The smtplib import is done inside the function (lazy import) to avoid loading
      the SMTP library at module import time.
"""

from fastapi import APIRouter, Depends

from app.middleware.auth import get_current_user

# Create the router instance. Mounted with prefix like "/api/channels/email".
router = APIRouter()


@router.post("/reply")
async def send_email_reply(
    data: dict,
    current_user: dict = Depends(get_current_user),
):
    """
    Send an email reply via SMTP.

    HTTP Method: POST
    URL: /reply
    Auth Required: Yes (called by agents from the dashboard)

    Request Body (dict):
        - to (str, required): The recipient's email address
        - subject (str, optional): Email subject line. Defaults to "Re: Support".
        - body (str, optional): The email body text (plain text, not HTML)

    Request Flow:
        1. Extract email settings (SMTP host, port, sender address, password)
           from the application configuration.
        2. Construct a MIMEText email message with the provided subject, body,
           from address (configured in settings), and to address.
        3. Connect to the SMTP server:
           a. Open a connection to the configured SMTP host and port
           b. Upgrade to a TLS-encrypted connection using STARTTLS
           c. Authenticate with the configured email credentials
           d. Send the email message
           e. The connection is automatically closed (using `with` context manager)
        4. If successful, return {"status": "sent"}.
        5. If any error occurs (bad credentials, network issue, etc.), catch the
           exception and return {"status": "error", "detail": "<error message>"}
           instead of crashing the endpoint.

    Response:
        - On success: {"status": "sent"}
        - On failure: {"status": "error", "detail": "<error description>"}
    """
    # Lazy imports to avoid loading SMTP libraries at module import time
    import smtplib
    from email.mime.text import MIMEText
    from app.config import get_settings
    from app.database import get_supabase
    from app.services import channel_registry as registry

    settings = get_settings()

    # Prefer the sending bot's own email credentials (configured in the
    # dashboard); fall back to the global .env values when bot_id is absent.
    creds: dict = {}
    bot_id = data.get("bot_id")
    if bot_id:
        result = (
            get_supabase()
            .table("bots")
            .select("*")
            .eq("id", bot_id)
            .eq("org_id", current_user["org_id"])
            .execute()
        )
        if result.data:
            creds = registry.resolve_credentials(result.data[0], "email")

    address = creds.get("address") or settings.email_address
    password = creds.get("app_password") or settings.email_password
    host = creds.get("smtp_host") or settings.email_smtp_host
    try:
        port = int(creds.get("smtp_port") or settings.email_smtp_port)
    except (TypeError, ValueError):
        port = settings.email_smtp_port

    # Construct the email message
    msg = MIMEText(data.get("body", ""))
    msg["Subject"] = data.get("subject", "Re: Support")
    msg["From"] = address
    msg["To"] = data.get("to", "")

    try:
        # Connect to SMTP server, encrypt with TLS, authenticate, and send
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(address, password)
            server.send_message(msg)
        return {"status": "sent"}
    except Exception as e:
        # Return error details instead of raising an exception, so the frontend
        # can display a user-friendly error message about the delivery failure
        return {"status": "error", "detail": str(e)}
