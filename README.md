# Follow the Money Series

**"Who funds corporate media?" with your favorite hosts.**

Two agents, Andrew (investigative reporter) and FJ (industry veteran) investigate the ownership structures behind major news publications using real-time data, then debate what it means for journalism and democracy.

Built for the [Cartesia x Anthropic Voice Agents Hackathon](https://cerebralvalley.ai/e/cartesia-voice-agents-hackathon) (SF, Feb 2026).

---

## What It Does

Pick a publication. Two AI characters investigate who really owns it — pulling live ownership data, government contracts, recent controversies — then discuss their findings with distinct voices and personalities.

**5 publications covered:** The Washington Post, Fox News, CNN, The New York Times, The Wall Street Journal

**What makes it different:**
- Characters have real personalities with selected voice from Cartesia's library
- Conversations reference events from *this week* via live web search
- Ownership data cross-referenced from curated dataset + Notion database + web
- Bias and factuality ratings sourced from [Ground News](https://ground.news/)

## Stack

| Layer | Technology | Role |
|-------|-----------|------|
| Reasoning | **Claude API** (claude-sonnet-4-20250514) | Agent personalities, web search, conversation generation |
| Voice | **Cartesia TTS API** (sonic-2) | Text-to-speech with distinct voices per character |
| Data | **Notion** database + JSON | Structured ownership data, queried at runtime |
| Web Search | Claude `web_search_20250305` | Real-time ownership developments, current events |
| Backend | **FastAPI** + Python | Orchestration, API endpoints |
| Frontend | HTML + CSS + JS | Editorial-style UI with audio playback |

## How It Works

```
User selects publication
        ↓
Orchestrator loads data from:
  - publications.json (curated dataset)
  - Notion database (structured ownership data)
        ↓
Claude generates conversation with web_search enabled:
  - Andrew (Reporter) investigates ownership + conflicts
  - FJ (Insider) adds industry commentary
  - 4 exchanges, alternating turns
        ↓
Cartesia TTS converts each turn to audio:
  - American voice for Andrew
  - British voice for FJ
        ↓
Web UI reveals turns sequentially with audio playback
```

## Hackathon Problem Statements

### Expressive
Two distinct character voices via Cartesia TTS — an American investigative reporter and a British industry insider. Personalities come through in both text and voice.

### Advanced Reasoning
Claude connects ownership structures to conflicts of interest, government contracts, editorial decisions, and recent controversies. Cross-references multiple data sources (curated dataset + Notion + live web).

### Situationally Aware
Claude's web search pulls current events in real-time. Demo conversations reference events from the same week they were generated (WaPo layoffs, Murdoch trust deals, Blue Origin/Pentagon meetings).

### Bonus: Notion Integration
Ownership data stored in a Notion database, queried at runtime via the Notion API. Publications migrated programmatically via `migrate_to_notion.py`.

## Characters & System Prompts

### Andrew — Reporter
*Inspired by Andrew Callaghan. American voice.*

> You are The Street Reporter, an investigative journalist who breaks down media ownership and corporate influence in accessible, direct language. Think Andrew Callaghan meets a media ownership watchdog.
>
> **Style:** You speak like you're explaining a conspiracy that's hiding in plain sight. Direct, punchy, no corporate jargon — you cut through the BS. You follow the money trail with relentless curiosity.
>
> **Approach:** Start by identifying WHO owns the publication and HOW they got it. Then follow the money — what are the owner's other business interests? Connect ownership to conflicts of interest. Always ask: "Who benefits from this arrangement?"
>
> **Rules:** Keep responses to 2-4 sentences per turn. Use specific dollar amounts, dates, and names. Speak naturally (converted to speech). When citing bias/factuality ratings, credit Ground News.

### FJ — Insider
*Inspired by Fonejacker. British voice.*

> You are The Insider, a witty and sarcastic media industry veteran who has seen it all from the inside. Think dry British humor meets media industry cynicism.
>
> **Style:** You deliver cutting commentary with a knowing smirk. Sarcastic but never mean-spirited — your humor serves the truth. You drop insider knowledge casually, as if everyone should already know these things.
>
> **Approach:** React to what the Reporter says with insider perspective. Add context they might not know — boardroom politics, editorial pressure, industry gossip. Point out the absurdity and irony in ownership structures. Your cynicism comes from caring.
>
> **Rules:** Keep responses to 2-4 sentences per turn. Tight, punchy delivery. When they present facts, you add the color commentary. Speak naturally (converted to speech). When citing bias/factuality, credit Ground News.

## Pipeline Process (per publication)

1. **Data** -- Add publication to `data/publications.json` with owner, ownership structure, conflicts of interest, controversies, Ground News ratings, and voice agent angles
2. **Notion** -- Migrate to the Notion database via API (row with properties + page body with detailed blocks). This gives agents a structured data source to query at runtime
3. **Generate conversation** -- Orchestrator loads the publication data from JSON + Notion, feeds it to Claude with `web_search` enabled. Claude's two personalities (Andrew and FJ) alternate 4 turns, pulling live data to supplement the curated dataset
4. **Generate audio** -- Each turn gets piped through Cartesia TTS with the agent's voice ID. WAV files saved to `demo/audio/{pub_id}/`
5. **Save demo** -- Conversation text + audio paths saved to `demo/{pub_id}_conversation.json`. The web UI loads this instantly without needing to regenerate
6. **UI auto-updates** -- Server reads `data/publications.json` for the publication list and checks `demo/` for pre-baked conversations. New publications appear immediately

## Setup

```bash
# Clone
git clone https://github.com/mmazco/newmedia.git
cd newmedia

# Environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# API keys
cp .env.example .env
# Add your keys to .env:
#   ANTHROPIC_API_KEY
#   CARTESIA_API_KEY
#   CARTESIA_VOICE_REPORTER  (pick from https://play.cartesia.ai/voices)
#   CARTESIA_VOICE_INSIDER
#   NOTION_API_KEY (optional)
#   NOTION_DATABASE_ID (optional)

# Run
python server.py
# Open http://localhost:8000
```

## Project Structure

```
├── server.py                  # FastAPI backend
├── src/
│   ├── agents/
│   │   ├── street_reporter.py # Andrew's personality prompt
│   │   └── insider.py         # FJ's personality prompt
│   ├── orchestrator.py        # Conversation turn-taking logic
│   ├── claude_client.py       # Claude API + web search
│   ├── cartesia_client.py     # TTS audio generation
│   └── notion_client.py       # Notion database reader
├── data/
│   └── publications.json      # Curated ownership dataset (5 publications)
├── assets/
│   ├── andrew-street-reporter-agent2.png  # Andrew character image
│   ├── fonejacker-insider-agent2.webp     # FJ character image
│   └── Öland, Lars Tunbjörk (1991).jpeg   # Footer artwork
├── web/
│   ├── index.html             # Frontend
│   ├── style.css              # Editorial design
│   ├── app.js                 # UI logic + audio playback
│   └── assets/                # Web-optimized images, favicon
├── demo/                      # Pre-baked conversations with audio
├── test_basic.py              # API smoke test
└── migrate_to_notion.py       # Notion database migration
```

## Credits

- Bias & factuality ratings: [Ground News](https://ground.news/)
- Footer artwork: [Lars Tunbjörk, Öland (1991)](https://www.blind-magazine.com/en/news/lars-tunbjork-a-view-from-the-side/)
- Made by [@mmazco](https://x.com/mmazco)
