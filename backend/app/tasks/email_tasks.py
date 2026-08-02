import asyncio
import imaplib
import email
from email.header import decode_header

from app.tasks.celery_app import celery_app
from app.config import get_settings


@celery_app.task
def check_inbox():
    """Check IMAP inbox for new emails and process them."""
    settings = get_settings()
    if not settings.email_address or not settings.email_password:
        return {"status": "email not configured"}

    try:
        mail = imaplib.IMAP4_SSL(settings.email_imap_host, settings.email_imap_port)
        mail.login(settings.email_address, settings.email_password)
        mail.select("inbox")

        # Search for unread emails
        _, message_numbers = mail.search(None, "UNSEEN")

        for num in message_numbers[0].split():
            _, msg_data = mail.fetch(num, "(RFC822)")
            email_body = msg_data[0][1]
            msg = email.message_from_bytes(email_body)

            # Extract info
            subject = decode_header(msg["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()

            from_addr = msg["From"]
            body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()

            if body:
                # Process through AI engine
                loop = asyncio.new_event_loop()
                loop.run_until_complete(_process_email(from_addr, subject, body))
                loop.close()

        mail.logout()
        return {"status": "ok", "processed": len(message_numbers[0].split())}

    except Exception as e:
        return {"status": "error", "detail": str(e)}


async def _process_email(from_addr: str, subject: str, body: str):
    """Process an email through the AI engine and send reply."""
    from app.database import get_supabase
    from app.services.ai_engine import AIEngine
    from app.services.conversation_manager import ConversationManager

    db = get_supabase()
    bots = db.table("bots").select("*").eq("is_active", True).execute()
    bot = None
    for b in bots.data or []:
        channels = b.get("channels", {})
        if isinstance(channels, dict) and channels.get("email"):
            bot = b
            break

    if not bot:
        return

    conv_manager = ConversationManager()
    conversation = await conv_manager.get_or_create(
        bot_id=bot["id"],
        channel="email",
        customer_id=from_addr,
        customer_name=from_addr,
    )

    await conv_manager.add_message(
        conversation_id=conversation["id"],
        role="customer",
        content=f"Subject: {subject}\n\n{body}",
    )

    history = await conv_manager.get_history(conversation["id"])
    ai_engine = AIEngine()
    result = await ai_engine.process_message(
        bot_id=bot["id"],
        message=body,
        conversation_history=history,
        bot_config=bot,
    )

    if not result["handoff"]:
        # Send email reply
        import smtplib
        from email.mime.text import MIMEText
        from app.config import get_settings

        settings = get_settings()
        reply = MIMEText(result["answer"])
        reply["Subject"] = f"Re: {subject}"
        reply["From"] = settings.email_address
        reply["To"] = from_addr

        with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port) as server:
            server.starttls()
            server.login(settings.email_address, settings.email_password)
            server.send_message(reply)

        await conv_manager.add_message(
            conversation_id=conversation["id"],
            role="ai",
            content=result["answer"],
        )
