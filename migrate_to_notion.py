#!/usr/bin/env python3
"""
Migrate publications.json to a Notion database.

Usage:
    source venv/bin/activate
    python migrate_to_notion.py
"""
import json
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

NOTION_VERSION = "2022-06-28"


def get_client():
    api_key = os.getenv("NOTION_API_KEY")
    if not api_key:
        print("Error: NOTION_API_KEY not set in .env")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    return httpx.Client(timeout=30.0, headers=headers)


def rich_text(content: str) -> list:
    """Create Notion rich_text. Truncate to 2000 chars (Notion limit)."""
    if not content:
        return [{"text": {"content": ""}}]
    return [{"text": {"content": content[:2000]}}]


def create_page(client: httpx.Client, database_id: str, pub: dict):
    """Create a single publication row in the Notion database."""
    # Join array fields into bullet-pointed text
    conflicts = "\n".join(f"• {c}" for c in pub.get("conflicts_of_interest", []))
    controversies = "\n".join(f"• {c}" for c in pub.get("recent_controversies", []))
    angles = pub.get("voice_agent_angles", {})
    rating = pub.get("ground_news_rating", {})

    properties = {
        "Publication": {"title": [{"text": {"content": pub["name"]}}]},
        "Owner": {"rich_text": rich_text(pub["owner"])},
        "Ownership Structure": {"rich_text": rich_text(pub.get("ownership_structure", ""))},
        "Current Status": {"rich_text": rich_text(pub.get("current_status", ""))},
        "Bias Rating": {"rich_text": rich_text(rating.get("bias", ""))},
    }

    r = client.post(
        "https://api.notion.com/v1/pages",
        json={"parent": {"database_id": database_id}, "properties": properties},
    )

    if r.status_code != 200:
        err = r.json()
        print(f"  ✗ {pub['name']}: {err.get('message', 'Unknown error')}")
        return False

    page_id = r.json()["id"]

    # Add detailed content as page body blocks
    blocks = []

    # Conflicts of Interest
    if conflicts:
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Conflicts of Interest"}}]},
        })
        for c in pub.get("conflicts_of_interest", []):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": c}}]},
            })

    # Recent Controversies
    if controversies:
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Recent Controversies"}}]},
        })
        for c in pub.get("recent_controversies", []):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": c}}]},
            })

    # Voice Agent Angles
    if angles:
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Voice Agent Angles"}}]},
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [
                {"text": {"content": "Street Reporter: "}, "annotations": {"bold": True}},
                {"text": {"content": angles.get("street_reporter", "")}},
            ]},
        })
        blocks.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [
                {"text": {"content": "Insider: "}, "annotations": {"bold": True}},
                {"text": {"content": angles.get("insider", "")}},
            ]},
        })

    # Extra details
    extras = []
    if pub.get("parent_company"):
        extras.append(f"Parent Company: {pub['parent_company']}")
    if pub.get("controlling_family"):
        extras.append(f"Controlling Family: {pub['controlling_family']}")
    if pub.get("key_figure"):
        extras.append(f"Key Figure: {pub['key_figure']}")
    if pub.get("year_acquired"):
        extras.append(f"Year Acquired: {pub['year_acquired']}")
    if pub.get("purchase_price"):
        extras.append(f"Purchase Price: {pub['purchase_price']}")
    if rating.get("factuality"):
        extras.append(f"Factuality: {rating['factuality']}")
    if rating.get("ownership_category"):
        extras.append(f"Category: {rating['ownership_category']}")

    if extras:
        blocks.append({
            "object": "block",
            "type": "heading_2",
            "heading_2": {"rich_text": [{"text": {"content": "Additional Details"}}]},
        })
        for detail in extras:
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": [{"text": {"content": detail}}]},
            })

    # Append blocks to the page
    if blocks:
        r2 = client.patch(
            f"https://api.notion.com/v1/blocks/{page_id}/children",
            json={"children": blocks},
        )
        if r2.status_code != 200:
            print(f"  ⚠ {pub['name']}: row created but couldn't add details")

    return True


def main():
    database_id = os.getenv("NOTION_DATABASE_ID")
    if not database_id:
        print("Error: NOTION_DATABASE_ID not set in .env")
        sys.exit(1)

    client = get_client()

    # Load publications
    with open("data/publications.json") as f:
        data = json.load(f)

    publications = data["publications"]
    print(f"Loaded {len(publications)} publications")
    print(f"Target database: {database_id}\n")

    print("Migrating...")
    success = 0
    for pub in publications:
        if create_page(client, database_id, pub):
            print(f"  ✓ {pub['name']}")
            success += 1

    client.close()
    print(f"\nDone! Migrated {success}/{len(publications)} publications to Notion.")


if __name__ == "__main__":
    main()
