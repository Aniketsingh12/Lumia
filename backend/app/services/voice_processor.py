"""
Voice Processor Service
========================

This module handles speech-to-text transcription for voice messages. When a
customer sends a voice note (e.g., a WhatsApp voice message), this service
downloads the audio and converts it to text so the AI engine can process it.

Why it exists:
- Voice messages are common on WhatsApp and other messaging platforms.
- The AI engine only works with text, so voice messages need to be transcribed
  before they can be processed through the pipeline.

How it fits in the architecture:
- Called by **webhook/chat API routes** when an incoming message contains audio.
- The channel_router identifies voice messages and stores the media ID/URL in
  the UnifiedMessage.voice_url field.
- This service downloads and transcribes the audio, producing text that is then
  fed to the AI engine like any other text message.

Technology:
- Uses **OpenAI Whisper API** (whisper-1 model) for transcription. Whisper
  supports many languages and handles noisy audio well.
- Audio files are temporarily saved to disk because the Whisper API expects
  file uploads, not raw bytes.
"""

import httpx
import tempfile
import os

from app.config import get_settings


_local_whisper_model = None  # lazy-loaded singleton


def _get_local_whisper():
    """Load faster-whisper once and reuse. Imported lazily so the dependency
    stays optional for users on the OpenAI Whisper API path."""
    global _local_whisper_model
    if _local_whisper_model is None:
        from faster_whisper import WhisperModel  # pip install faster-whisper

        settings = get_settings()
        _local_whisper_model = WhisperModel(
            settings.local_whisper_model,
            device="cpu",
            compute_type="int8",
        )
    return _local_whisper_model


def _transcribe_file_local(path: str) -> str:
    """Transcribe a local audio file with faster-whisper (free, offline)."""
    model = _get_local_whisper()
    segments, _info = model.transcribe(path)
    return "".join(seg.text for seg in segments).strip()


async def _transcribe_file_openai(path: str) -> str:
    """Transcribe a local audio file with OpenAI Whisper API."""
    settings = get_settings()
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    with open(path, "rb") as audio_file:
        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
        )
    return transcript.text


async def _transcribe_file(path: str) -> str:
    """Route to the configured voice provider."""
    settings = get_settings()
    if settings.voice_provider == "local":
        return _transcribe_file_local(path)
    return await _transcribe_file_openai(path)


async def transcribe(audio_url: str) -> str:
    """
    Download an audio file from a URL and transcribe it to text.

    Routes to OpenAI Whisper API or local faster-whisper based on
    `VOICE_PROVIDER` in settings. Local mode requires `pip install faster-whisper`
    and works fully offline / for free.

    Args:
        audio_url: A publicly accessible URL pointing to an audio file.

    Returns:
        The transcribed text content of the audio.
    """
    # Step 1: Download the audio file from the URL
    async with httpx.AsyncClient() as client:
        response = await client.get(audio_url)
        response.raise_for_status()

    # Step 2: Save to a temp file (whisper APIs / models need a file path)
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        return await _transcribe_file(tmp_path)
    finally:
        os.unlink(tmp_path)


async def transcribe_whatsapp_media(media_id: str) -> str:
    """
    Download a WhatsApp voice message by its media ID and transcribe it.

    WhatsApp doesn't give us a direct download URL in the webhook. Instead,
    it provides a media ID. We need to:
    1. Call the Graph API to get the actual download URL for that media ID.
    2. Download the audio using that URL (with authentication).
    3. Transcribe the downloaded audio.

    This two-step download process is required because WhatsApp media URLs
    are short-lived and require the access token for authentication.

    Args:
        media_id: The WhatsApp media ID from the webhook payload (found in
                  the UnifiedMessage.voice_url field after normalization).

    Returns:
        The transcribed text content of the voice message.

    Raises:
        httpx.HTTPStatusError: If the media URL lookup or download fails.
        openai.APIError: If the Whisper transcription fails.
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        # Step 1: Get the actual media download URL from WhatsApp's Graph API
        # The media ID from the webhook is just a reference -- we need to
        # resolve it to a real URL first
        resp = await client.get(
            f"https://graph.facebook.com/v18.0/{media_id}",
            headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
        )
        resp.raise_for_status()
        media_url = resp.json().get("url")

        # Step 2: Download the actual audio file using the resolved URL
        # Note: The download also requires the WhatsApp token for auth
        media_resp = await client.get(
            media_url,
            headers={"Authorization": f"Bearer {settings.whatsapp_token}"},
        )
        media_resp.raise_for_status()

    # Step 3: Save to a temp file and transcribe via the configured provider
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
        tmp.write(media_resp.content)
        tmp_path = tmp.name

    try:
        return await _transcribe_file(tmp_path)
    finally:
        os.unlink(tmp_path)
