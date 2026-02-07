"""
Conversation orchestrator.
Coordinates turn-taking between The Street Reporter and The Insider.
"""
import json
import os
import sys

from src.agents.street_reporter import STREET_REPORTER_PROMPT
from src.agents.insider import INSIDER_PROMPT
from src.claude_client import get_agent_response
from src.cartesia_client import generate_conversation_audio
from src.notion_client import format_notion_context


def load_publications() -> dict:
    """Load publications dataset."""
    data_path = os.path.join(os.path.dirname(__file__), "..", "data", "publications.json")
    with open(data_path) as f:
        return json.load(f)


def format_publication_context(pub: dict) -> str:
    """Format a publication's data into a context string for the agents."""
    rating = pub.get("ground_news_rating", {})
    angles = pub.get("voice_agent_angles", {})

    conflicts = "\n".join(f"  - {c}" for c in pub.get("conflicts_of_interest", []))
    controversies = "\n".join(f"  - {c}" for c in pub.get("recent_controversies", []))

    context = f"""PUBLICATION: {pub['name']}
OWNER: {pub['owner']}
OWNERSHIP STRUCTURE: {pub.get('ownership_structure', 'Unknown')}
YEAR ACQUIRED: {pub.get('year_acquired', 'Unknown')}
PURCHASE PRICE: {pub.get('purchase_price', 'N/A')}
PARENT COMPANY: {pub.get('parent_company', 'N/A')}
CONTROLLING FAMILY: {pub.get('controlling_family', 'N/A')}
KEY FIGURE: {pub.get('key_figure', 'N/A')}
CURRENT STATUS: {pub.get('current_status', 'Unknown')}

GROUND NEWS RATINGS:
  Bias: {rating.get('bias', 'Unknown')}
  Factuality: {rating.get('factuality', 'Unknown')}
  Ownership Category: {rating.get('ownership_category', 'Unknown')}

CONFLICTS OF INTEREST:
{conflicts}

RECENT CONTROVERSIES:
{controversies}

SUGGESTED ANGLES:
  Street Reporter: {angles.get('street_reporter', '')}
  Insider: {angles.get('insider', '')}"""

    return context


def run_conversation(pub: dict, num_exchanges: int = 4, use_web_search: bool = False) -> list[dict]:
    """
    Run a conversation between the two agents about a publication.

    Args:
        pub: Publication data dict.
        num_exchanges: Number of back-and-forth exchanges (each = 2 turns).
        use_web_search: If True, enable Claude web_search for real-time data.

    Returns:
        List of conversation turns: [{"agent": str, "text": str}, ...]
    """
    context = format_publication_context(pub)

    # Try to enrich with Notion data
    try:
        notion_context = format_notion_context(pub["name"])
        if notion_context:
            context += f"\n\n{notion_context}"
    except Exception as e:
        print(f"  (Notion lookup skipped: {e})")

    conversation_log = []

    # Build the opening prompt that both agents will see
    web_search_note = (
        "\n\nYou have access to web search. Use it to find the latest ownership "
        "developments if the data above seems outdated or if you want to verify facts."
        if use_web_search else ""
    )

    opening = (
        f"Let's discuss the ownership of {pub['name']}. "
        f"Here's what we know:\n\n{context}\n\n"
        f"Start by breaking down who really owns this publication and what that means."
        f"{web_search_note}"
    )

    # Track messages for each agent's perspective
    # Street Reporter sees: user prompts + their own responses + Insider's responses
    # Insider sees: the same conversation but from their perspective
    reporter_messages = []
    insider_messages = []

    for i in range(num_exchanges):
        # --- Street Reporter's turn ---
        if i == 0:
            # First turn: Reporter opens with the investigation
            reporter_messages.append({"role": "user", "content": opening})
        else:
            # Subsequent turns: Reporter responds to Insider's last comment
            reporter_messages.append({
                "role": "user",
                "content": f"The Insider just said: \"{conversation_log[-1]['text']}\"\n\nRespond to that and dig deeper.",
            })

        reporter_response = get_agent_response(STREET_REPORTER_PROMPT, reporter_messages, use_web_search=use_web_search)
        reporter_messages.append({"role": "assistant", "content": reporter_response})

        conversation_log.append({
            "agent": "Street Reporter",
            "text": reporter_response,
        })

        print(f"\n🎤 STREET REPORTER:\n{reporter_response}")

        # --- Insider's turn ---
        if i == 0:
            # First turn: Insider reacts to Reporter's opening
            insider_messages.append({
                "role": "user",
                "content": (
                    f"We're discussing the ownership of {pub['name']}. "
                    f"Here's the background:\n\n{context}\n\n"
                    f"The Street Reporter just said: \"{reporter_response}\"\n\n"
                    f"React to that with your insider perspective."
                ),
            })
        else:
            # Subsequent turns: Insider responds to Reporter's latest
            insider_messages.append({
                "role": "user",
                "content": f"The Street Reporter just said: \"{reporter_response}\"\n\nRespond with your insider take.",
            })

        insider_response = get_agent_response(INSIDER_PROMPT, insider_messages, use_web_search=use_web_search)
        insider_messages.append({"role": "assistant", "content": insider_response})

        conversation_log.append({
            "agent": "Insider",
            "text": insider_response,
        })

        print(f"\n🎭 INSIDER:\n{insider_response}")

    return conversation_log


def select_publication(publications: list[dict]) -> dict:
    """Let user pick a publication from the list."""
    print("\n" + "=" * 60)
    print("  FOLLOW THE MONEY: Media Ownership Investigation")
    print("=" * 60)
    print("\nSelect a publication to investigate:\n")

    for i, pub in enumerate(publications, 1):
        rating = pub.get("ground_news_rating", {})
        print(f"  {i}. {pub['name']}")
        print(f"     Owner: {pub['owner']}")
        print(f"     Ground News Bias: {rating.get('bias', 'Unknown')}")
        print()

    while True:
        try:
            choice = input("Enter number (1-5): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(publications):
                return publications[idx]
            print("Please enter a number between 1 and 5.")
        except (ValueError, EOFError):
            print("Please enter a valid number.")


def main(pub_id: str | None = None, with_audio: bool = False):
    """Main entry point."""
    data = load_publications()
    publications = data["publications"]

    # Check for command-line argument or passed pub_id (for non-interactive mode)
    cli_args = sys.argv[1:]
    use_web_search = False

    if "--audio" in cli_args:
        with_audio = True
        cli_args.remove("--audio")
    if "--web-search" in cli_args:
        use_web_search = True
        cli_args.remove("--web-search")

    pub_id = pub_id or (cli_args[0].lower() if cli_args else None)
    if pub_id:
        pub = next((p for p in publications if p["id"] == pub_id), None)
        if not pub:
            print(f"Unknown publication ID: {pub_id}")
            print(f"Available: {', '.join(p['id'] for p in publications)}")
            sys.exit(1)
    else:
        pub = select_publication(publications)

    print(f"\n{'=' * 60}")
    print(f"  Investigating: {pub['name']}")
    print(f"  Owner: {pub['owner']}")
    rating = pub.get("ground_news_rating", {})
    print(f"  Ground News Bias Rating: {rating.get('bias', 'Unknown')}")
    print(f"  Ground News Factuality: {rating.get('factuality', 'Unknown')}")
    print(f"{'=' * 60}")

    num_exchanges = 4
    print(f"\n  Starting {num_exchanges}-round conversation...\n")

    if use_web_search:
        print("  Web search: ENABLED")

    conversation = run_conversation(pub, num_exchanges=num_exchanges, use_web_search=use_web_search)

    print(f"\n{'=' * 60}")
    print(f"  Conversation complete: {len(conversation)} turns")
    print(f"{'=' * 60}")

    # Generate audio if requested
    if with_audio:
        print(f"\n  Generating audio for {len(conversation)} turns...")
        output_dir = f"audio_output/{pub['id']}"
        results = generate_conversation_audio(conversation, output_dir=output_dir)
        print(f"\n  Audio saved to {output_dir}/")
        for r in results:
            print(f"    {r['audio_path']}")
        return results

    return conversation


if __name__ == "__main__":
    main()
