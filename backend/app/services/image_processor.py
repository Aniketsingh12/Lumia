"""
Image Processor Service
========================

This module handles image understanding for messages that contain photos or
screenshots. When a customer sends an image, this service downloads it and
uses Claude's Vision capabilities to generate a text description that the
AI engine can work with.

Why it exists:
- Customers sometimes send photos instead of (or in addition to) text -- for
  example, a screenshot of an error, a photo of a product, or an image of a
  receipt.
- The AI engine works with text, so images need to be "translated" into text
  descriptions before they can be processed through the pipeline.

How it fits in the architecture:
- Called by **webhook/chat API routes** when an incoming message contains an
  image (identified by the UnifiedMessage.image_url field).
- The resulting text description is either appended to the customer's message
  or used as the message content, then fed to the AI engine.
- Depends on **llm_client.py** (specifically the `vision()` method) for the
  actual image analysis.

Technology:
- Uses **Claude Vision** (via LLMClient.vision()) which can understand and
  describe images, read text in images (OCR), and identify objects/products.
"""

import httpx

from app.services.llm_client import LLMClient


async def describe_image(image_url: str, context: str = "") -> str:
    """
    Download an image from a URL and generate a text description using Claude Vision.

    Data flow:
    1. Download the image from the provided URL using httpx.
    2. Create an LLMClient instance to access Claude Vision.
    3. Build a prompt that instructs Claude to describe the image, focusing on
       text, products, and relevant information.
    4. If additional context is provided (e.g., the customer's accompanying
       text message), include it in the prompt so Claude can focus on what's
       relevant.
    5. Send the image bytes and prompt to Claude Vision.
    6. Return the text description.

    Example use case:
    - Customer sends a photo of a damaged product with caption "look at this".
    - This function downloads the image, sends it to Claude Vision, and returns
      something like: "The image shows a smartphone with a cracked screen. The
      crack extends from the top-left corner to the bottom-right..."
    - This description is then fed to the AI engine, which can formulate an
      appropriate customer support response.

    Args:
        image_url: A publicly accessible URL pointing to the image file.
        context: Optional additional context to help Claude focus its description.
                 For example, the customer's text message that accompanied the
                 image, or the type of bot (e.g., "tech support").

    Returns:
        A text description of the image content.

    Raises:
        httpx.HTTPStatusError: If the image download fails.
    """
    # Step 1: Download the image from the URL
    async with httpx.AsyncClient() as client:
        response = await client.get(image_url)
        response.raise_for_status()

    # Step 2: Set up the LLM client for vision
    llm = LLMClient()

    # Step 3: Build the prompt -- tell Claude what to focus on
    prompt = "Describe this image in detail, focusing on any text, products, or relevant information."
    if context:
        # If we have context (e.g., the customer's message), include it so
        # Claude can tailor its description to what's relevant
        prompt += f"\n\nContext: {context}"

    # Step 4 & 5: Send image bytes + prompt to Claude Vision and return the description
    return await llm.vision(response.content, prompt)
