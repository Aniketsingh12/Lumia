import re


def validate_phone_number(phone: str) -> bool:
    """Validate international phone number format."""
    pattern = r"^\+?[1-9]\d{7,14}$"
    return bool(re.match(pattern, phone.replace(" ", "").replace("-", "")))


def validate_url(url: str) -> bool:
    """Validate URL format."""
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, url))


def sanitize_input(text: str, max_length: int = 5000) -> str:
    """Sanitize user input text."""
    # Remove null bytes
    text = text.replace("\x00", "")
    # Truncate
    text = text[:max_length]
    return text.strip()


def validate_file_size(size: int, max_mb: int = 10) -> bool:
    """Check file size is within limits."""
    return size <= max_mb * 1024 * 1024
