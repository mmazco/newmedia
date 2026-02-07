"""
Cartesia TTS client.
Converts agent text responses to speech audio.
"""
import os
from pathlib import Path

from cartesia import Cartesia
from dotenv import load_dotenv

load_dotenv()

MODEL = "sonic-2"
OUTPUT_FORMAT = {
    "container": "wav",
    "sample_rate": 44100,
    "encoding": "pcm_s16le",
    "bit_rate": 128000,
}

# Voice IDs from Cartesia voice library (https://play.cartesia.ai/voices)
# Street Reporter: American, confident, clear
# Insider: British, witty, conversational
VOICE_IDS = {
    "Street Reporter": os.getenv("CARTESIA_VOICE_REPORTER", ""),
    "Insider": os.getenv("CARTESIA_VOICE_INSIDER", ""),
}

_client = None


def get_client() -> Cartesia:
    """Get or create the Cartesia client (singleton)."""
    global _client
    if _client is None:
        _client = Cartesia(api_key=os.getenv("CARTESIA_API_KEY"))
    return _client


def text_to_speech(text: str, agent_name: str, output_path: str | None = None) -> bytes:
    """
    Convert text to speech audio using the agent's voice.

    Args:
        text: The text to speak.
        agent_name: "Street Reporter" or "Insider" -- determines voice.
        output_path: Optional file path to save the WAV file.

    Returns:
        Raw audio bytes (WAV format).
    """
    client = get_client()
    voice_id = VOICE_IDS.get(agent_name, "")

    if not voice_id:
        raise ValueError(
            f"No voice ID configured for '{agent_name}'. "
            f"Set CARTESIA_VOICE_REPORTER and CARTESIA_VOICE_INSIDER in .env"
        )

    audio_chunks = client.tts.bytes(
        model_id=MODEL,
        transcript=text,
        voice={"id": voice_id},
        output_format=OUTPUT_FORMAT,
        language="en",
    )

    audio_data = b"".join(audio_chunks)

    if output_path:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(audio_data)

    return audio_data


def generate_conversation_audio(
    conversation: list[dict],
    output_dir: str = "audio_output",
) -> list[dict]:
    """
    Generate audio files for an entire conversation.

    Args:
        conversation: List of {"agent": str, "text": str} dicts from orchestrator.
        output_dir: Directory to save WAV files.

    Returns:
        List of {"agent": str, "text": str, "audio_path": str} dicts.
    """
    results = []

    for i, turn in enumerate(conversation):
        agent = turn["agent"]
        text = turn["text"]
        filename = f"{output_dir}/turn_{i:02d}_{agent.lower().replace(' ', '_')}.wav"

        print(f"  Generating audio for turn {i + 1}: {agent}...")
        text_to_speech(text, agent, output_path=filename)

        results.append({
            "agent": agent,
            "text": text,
            "audio_path": filename,
        })

    return results
