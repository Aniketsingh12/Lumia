import re


def format_for_whatsapp(answer: str, sources: list[dict]) -> str:
    """Format response for WhatsApp (plain text with emoji)."""
    # Remove confidence tag
    clean = re.sub(r"\[Confidence:\s*\d+/10\]", "", answer).strip()

    if sources:
        clean += "\n\n📚 Sources:"
        for s in sources[:3]:
            meta = s.get("metadata", {})
            doc_id = meta.get("doc_id", "")
            clean += f"\n• Document {doc_id[:8]}"

    return clean


def format_for_slack(answer: str, sources: list[dict]) -> dict:
    """Format response as Slack Block Kit message."""
    clean = re.sub(r"\[Confidence:\s*\d+/10\]", "", answer).strip()

    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": clean}},
    ]

    if sources:
        source_text = "*Sources:*\n"
        for s in sources[:3]:
            content_preview = s.get("content", "")[:80]
            source_text += f"• _{content_preview}_\n"
        blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": source_text}]})

    return {"blocks": blocks}


def format_for_widget(answer: str, sources: list[dict]) -> dict:
    """Format response for web widget (HTML-safe)."""
    clean = re.sub(r"\[Confidence:\s*\d+/10\]", "", answer).strip()

    return {
        "text": clean,
        "html": clean.replace("\n", "<br>"),
        "sources": [
            {
                "preview": s.get("content", "")[:100],
                "metadata": s.get("metadata", {}),
            }
            for s in sources[:3]
        ],
    }
