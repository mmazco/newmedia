#!/usr/bin/env python3
"""
Phase 0.5: Critical API Smoke Test
Run this FIRST to verify APIs work before building anything.

Usage:
    source venv/bin/activate
    python test_basic.py
"""
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def test_claude_api():
    """Test Claude API connection and basic response."""
    print("\n[1/2] Testing Claude API...")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("  ✗ ANTHROPIC_API_KEY not set in .env")
        return False

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[
                {
                    "role": "user",
                    "content": "In one sentence, who owns The Washington Post?",
                }
            ],
        )

        text = response.content[0].text
        print(f"  ✓ Claude API works!")
        print(f"  Model: {response.model}")
        print(f"  Response: {text[:120]}")
        print(f"  Tokens used: {response.usage.input_tokens} in / {response.usage.output_tokens} out")
        return True

    except Exception as e:
        print(f"  ✗ Claude API failed: {e}")
        return False


def test_cartesia_api():
    """Test Cartesia TTS API connection and audio generation."""
    print("\n[2/2] Testing Cartesia API...")

    api_key = os.getenv("CARTESIA_API_KEY")
    if not api_key:
        print("  ✗ CARTESIA_API_KEY not set in .env")
        return False

    try:
        from cartesia import Cartesia

        client = Cartesia(api_key=api_key)

        # Test: list available voices (lightweight, no audio credits used)
        voices_pager = client.voices.list()
        voices = list(voices_pager)
        voice_count = len(voices)
        print(f"  ✓ Cartesia API connected! ({voice_count} voices available)")

        # Show a few sample voices for selection later
        print("  Sample voices:")
        for v in voices[:5]:
            name = v.name if hasattr(v, "name") else v.get("name", "unknown")
            vid = v.id if hasattr(v, "id") else v.get("id", "unknown")
            print(f"    - {name} (id: {str(vid)[:12]}...)")

        # Test: generate a tiny audio clip to verify TTS works
        print("\n  Testing TTS generation...")
        first_voice = voices[0]
        test_voice_id = first_voice.id if hasattr(first_voice, "id") else first_voice["id"]
        test_voice_name = first_voice.name if hasattr(first_voice, "name") else first_voice.get("name", "unknown")

        audio_chunks = client.tts.bytes(
            model_id="sonic-2",
            transcript="Testing, one two three.",
            voice={"id": test_voice_id},
            output_format={
                "container": "wav",
                "sample_rate": 44100,
                "encoding": "pcm_s16le",
                "bit_rate": 128000,
            },
            language="en",
        )

        audio_data = b"".join(audio_chunks)
        audio_size = len(audio_data)
        print(f"  ✓ TTS works! Generated {audio_size:,} bytes of audio")
        print(f"  Test voice: {test_voice_name}")

        return True

    except Exception as e:
        print(f"  ✗ Cartesia API failed: {e}")
        return False


def main():
    print("=" * 50)
    print("  PHASE 0.5: API SMOKE TEST")
    print("  Verifying all APIs before development")
    print("=" * 50)

    claude_ok = test_claude_api()
    cartesia_ok = test_cartesia_api()

    print("\n" + "=" * 50)
    print("  RESULTS")
    print("=" * 50)
    print(f"  Claude API:   {'✓ PASS' if claude_ok else '✗ FAIL'}")
    print(f"  Cartesia API: {'✓ PASS' if cartesia_ok else '✗ FAIL'}")

    if claude_ok and cartesia_ok:
        print("\n  All APIs working. Safe to proceed with Phase 1!")
        return 0
    else:
        print("\n  Fix failing APIs before continuing development.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
