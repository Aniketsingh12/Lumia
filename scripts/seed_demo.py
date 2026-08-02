"""Seed demo data for BotForge presentations."""
import uuid
from datetime import datetime, timedelta, timezone
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import get_supabase


def seed():
    db = get_supabase()
    now = datetime.now(timezone.utc)

    # Create demo org
    org_id = str(uuid.uuid4())
    db.table("organizations").insert({
        "id": org_id,
        "name": "Demo Company",
        "plan": "free",
    }).execute()

    # Create demo user
    user_id = str(uuid.uuid4())
    from passlib.hash import bcrypt
    db.table("users").insert({
        "id": user_id,
        "email": "demo@botforge.app",
        "full_name": "Demo User",
        "password_hash": bcrypt.hash("demo123"),
        "org_id": org_id,
        "role": "owner",
    }).execute()

    db.table("organizations").update({"owner_id": user_id}).eq("id", org_id).execute()

    # Create demo bot
    bot_id = str(uuid.uuid4())
    db.table("bots").insert({
        "id": bot_id,
        "org_id": org_id,
        "name": "ShopBot",
        "tone": "friendly",
        "greeting_message": "Hey there! I'm ShopBot. Ask me anything about our products!",
        "fallback_message": "Hmm, I'm not sure about that. Let me get a human to help you.",
        "custom_rules": ["Never mention competitor names", "Always suggest related products"],
        "channels": {"website": True, "whatsapp": None},
        "is_active": True,
        "message_count": 1247,
        "doc_count": 5,
        "created_at": (now - timedelta(days=7)).isoformat(),
    }).execute()

    # Create demo conversations
    channels = ["website", "whatsapp", "instagram", "website", "slack"]
    statuses = ["active", "resolved", "escalated", "resolved", "active"]
    names = ["Priya Sharma", "Rahul Verma", "Anita Desai", "Vikram Patel", "Sneha Rao"]

    for i in range(5):
        conv_id = str(uuid.uuid4())
        db.table("conversations").insert({
            "id": conv_id,
            "bot_id": bot_id,
            "channel": channels[i],
            "customer_name": names[i],
            "customer_id": f"customer-{i}",
            "status": statuses[i],
            "ai_resolution": statuses[i] == "resolved",
            "last_message": f"Sample message from {names[i]}",
            "message_count": (i + 1) * 3,
            "started_at": (now - timedelta(hours=i * 12)).isoformat(),
        }).execute()

    print(f"Demo data seeded!")
    print(f"  Email: demo@botforge.app")
    print(f"  Password: demo123")
    print(f"  Bot: ShopBot ({bot_id})")


if __name__ == "__main__":
    seed()
