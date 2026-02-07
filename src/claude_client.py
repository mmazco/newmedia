"""
Claude API client wrapper.
Handles message creation with system prompts for agent personalities.
Supports web_search tool for real-time data.
"""
import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 300

_client = None


def get_client() -> Anthropic:
    """Get or create the Anthropic client (singleton)."""
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def get_agent_response(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = MAX_TOKENS,
    use_web_search: bool = False,
) -> str:
    """
    Get a response from Claude using a specific agent personality.

    Args:
        system_prompt: The agent's system prompt (personality definition).
        messages: Conversation history in Claude message format.
        max_tokens: Max response length.
        use_web_search: If True, enable Claude's web_search tool.

    Returns:
        The agent's text response.
    """
    client = get_client()

    kwargs = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": messages,
    }

    if use_web_search:
        kwargs["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]

    response = client.messages.create(**kwargs)

    # Extract text from response, handling tool use blocks
    text_parts = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)

    return "".join(text_parts)
