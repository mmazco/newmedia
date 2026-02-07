"""
Notion database reader.
Queries the media ownership database for structured publication data.
"""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

NOTION_VERSION = "2022-06-28"

_client = None


def _get_client() -> httpx.Client:
    """Get or create the HTTP client with Notion headers."""
    global _client
    if _client is None:
        api_key = os.getenv("NOTION_API_KEY")
        if not api_key:
            raise ValueError("NOTION_API_KEY not set in .env")
        _client = httpx.Client(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Notion-Version": NOTION_VERSION,
            },
        )
    return _client


def _extract_text(prop: dict) -> str:
    """Extract plain text from a Notion property value."""
    prop_type = prop.get("type", "")

    if prop_type == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    elif prop_type == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    elif prop_type == "select":
        sel = prop.get("select")
        return sel.get("name", "") if sel else ""
    elif prop_type == "number":
        return str(prop.get("number", ""))
    else:
        return ""


def query_publications() -> list[dict]:
    """
    Query all publications from the Notion database.

    Returns:
        List of publication dicts with flattened properties.
    """
    client = _get_client()
    db_id = os.getenv("NOTION_DATABASE_ID")
    if not db_id:
        raise ValueError("NOTION_DATABASE_ID not set in .env")

    r = client.post(f"https://api.notion.com/v1/databases/{db_id}/query", json={})
    if r.status_code != 200:
        raise RuntimeError(f"Notion query failed: {r.status_code} {r.json().get('message', '')}")

    results = []
    for page in r.json().get("results", []):
        props = page.get("properties", {})
        pub = {}
        for name, value in props.items():
            pub[name] = _extract_text(value)
        pub["page_id"] = page["id"]
        results.append(pub)

    return results


def query_publication_by_name(name: str) -> dict | None:
    """
    Find a specific publication by name.

    Args:
        name: Publication name to search for (partial match).

    Returns:
        Publication dict or None if not found.
    """
    pubs = query_publications()
    name_lower = name.lower()
    for pub in pubs:
        if name_lower in pub.get("Publication", "").lower():
            return pub
    return None


def get_publication_details(page_id: str) -> dict:
    """
    Get full page content (blocks) for a publication.

    Args:
        page_id: The Notion page ID.

    Returns:
        Dict with page properties and body content.
    """
    client = _get_client()

    # Get page blocks (body content)
    r = client.get(f"https://api.notion.com/v1/blocks/{page_id}/children")
    if r.status_code != 200:
        return {"blocks": []}

    blocks = []
    for block in r.json().get("results", []):
        block_type = block.get("type", "")
        content = block.get(block_type, {})
        texts = content.get("rich_text", [])
        text = "".join(t.get("plain_text", "") for t in texts)
        if text:
            blocks.append({"type": block_type, "text": text})

    return {"blocks": blocks}


def format_notion_context(pub_name: str) -> str:
    """
    Format Notion data for a publication into a context string for agents.

    Args:
        pub_name: Publication name to look up.

    Returns:
        Formatted string with Notion data, or empty string if not found.
    """
    pub = query_publication_by_name(pub_name)
    if not pub:
        return ""

    lines = ["DATA FROM NOTION DATABASE:"]
    for key, value in pub.items():
        if key == "page_id" or not value:
            continue
        lines.append(f"  {key}: {value}")

    # Get detailed page content
    details = get_publication_details(pub["page_id"])
    if details.get("blocks"):
        lines.append("\nDETAILED NOTES:")
        for block in details["blocks"]:
            prefix = "  - " if block["type"] == "bulleted_list_item" else "  "
            lines.append(f"{prefix}{block['text']}")

    return "\n".join(lines)
