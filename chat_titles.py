"""Small, deterministic chat titles without an extra model request."""


def make_chat_title(message: str, max_length: int = 50) -> str:
    """Build a readable title from the first user message without network latency."""
    if not isinstance(message, str) or max_length < 1:
        return "New chat"
    text = " ".join(message.split()).strip(" \t\r\n.,!?;:-")
    if not text:
        return "New chat"
    if len(text) <= max_length:
        return text
    shortened = text[: max_length + 1].rsplit(" ", 1)[0].strip(" ,.;:-")
    return shortened or text[:max_length].rstrip()
