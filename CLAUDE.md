# CLAUDE.md — Project Context for AI Assistants

## Project Overview

Generate Anki-compatible flashcard decks (`.apkg` files) for the **New Practical Chinese Reader (3rd Edition)**. Each lesson produces a deck containing **all main characters** and **all supplementary characters** with:

- Chinese character display
- Pinyin romanization
- English definition
- Stroke order animation (via Hanzi Writer)
- Audio pronunciation (via Azure Speech TTS, with gTTS fallback)

## Architecture

```
Flashcards/
├── CLAUDE.md              # This file — AI context
├── README.md              # Project documentation
├── pyproject.toml         # Python project config (uv/pip)
├── requirements.txt       # Pinned dependencies
├── src/
│   ├── __init__.py
│   ├── generate_deck.py   # Main entry point — builds .apkg files
│   ├── models.py          # genanki Model/Note definitions
│   ├── audio.py           # Azure Speech TTS — generates mp3 per character
│   ├── stroke_order.py    # Generates stroke order HTML using Hanzi Writer JS
│   ├── characters.py      # Character data per lesson (source of truth)
│   └── extract_table.py   # Image → lesson JSON via Azure DI / Gemini / Ollama
├── data/
│   └── lessons/           # Per-lesson JSON character lists
│       ├── lesson_01.json
│       └── ...
├── output/                # Generated .apkg files (gitignored)
│   └── media/             # Generated mp3 + stroke images (gitignored)
├── templates/
│   └── card.html          # Anki card HTML template with Hanzi Writer embed
└── tests/
    └── test_generate.py   # Basic smoke tests
```

## Key Technologies

| Tool | Purpose | Docs |
|------|---------|------|
| **genanki** | Python library for generating `.apkg` Anki decks | https://github.com/kerrickstaley/genanki |
| **Azure Speech** | Neural TTS via Azure REST API — high-quality mp3 audio | https://learn.microsoft.com/en-us/azure/ai-services/speech-service/ |
| **gTTS** | Free TTS fallback via Google Translate API | https://github.com/pndurette/gTTS |
| **Hanzi Writer** | JS library for stroke order animations (embedded in card HTML) | https://hanziwriter.org/docs.html |
| **hanzi-writer-data** | Stroke data for all CJK characters | https://github.com/chanind/hanzi-writer-data |
| **Azure Document Intelligence** | Structured table extraction from photos (prebuilt-layout model) — primary backend | https://learn.microsoft.com/en-us/azure/ai-services/document-intelligence/ |
| **Gemini 2.5 Flash** | Vision LLM fallback for table extraction | https://ai.google.dev/ |
| **Ollama** | Local vision LLM fallback for table extraction | https://ollama.com |

## Anki Deck Generation (genanki)

### Core Concepts
- **Model**: defines fields + card templates (need a stable `model_id`)
- **Note**: a single fact (one Chinese character) with field values
- **Deck**: a collection of notes (need a stable `deck_id`)
- **Package**: wraps deck + media files into `.apkg`

### Our Model Fields
1. `Character` — the Chinese character (e.g. 你)
2. `Pinyin` — romanization (e.g. nǐ)
3. `English` — definition (e.g. you)
4. `Audio` — `[sound:char_XXXX.mp3]` reference
5. `StrokeOrder` — HTML/JS snippet for Hanzi Writer animation
6. `CharacterType` — "main" or "supplementary"
7. `Lesson` — lesson number

### Card Templates
- **Card 1 (Recognition)**: Front shows Character + Audio, Back shows Pinyin + English + StrokeOrder
- **Card 2 (Recall)**: Front shows English, Back shows Character + Pinyin + Audio + StrokeOrder

### Media Files
- Audio files: named `char_{unicode_codepoint}.mp3` (e.g. `char_4F60.mp3` for 你)
- Media files are added to `Package.media_files` list with full paths
- In note fields, reference by filename only: `[sound:char_4F60.mp3]`

## Character Data Format (per lesson JSON)

```json
{
  "lesson": 1,
  "title": "你好",
  "characters": {
    "main": [
      {
        "character": "你",
        "pinyin": "nǐ",
        "english": "you"
      }
    ],
    "supplementary": [
      {
        "character": "您",
        "pinyin": "nín",
        "english": "you (polite)"
      }
    ]
  }
}
```

## Audio Generation (Azure Speech TTS)

Primary backend uses Azure Speech REST API with `zh-CN-XiaoxiaoNeural` voice:

```python
import requests

url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
ssml = "<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='zh-CN'><voice name='zh-CN-XiaoxiaoNeural'>你</voice></speak>"
headers = {
    "Ocp-Apim-Subscription-Key": key,
    "Content-Type": "application/ssml+xml",
    "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
}
resp = requests.post(url, headers=headers, data=ssml.encode("utf-8"))
```

### Setup
```bash
export AZURE_SPEECH_KEY=your-key
export AZURE_SPEECH_REGION=eastus   # or your chosen region
```

- Voice: `zh-CN-XiaoxiaoNeural` (clear, natural female Mandarin)
- Falls back to gTTS if Azure env vars are not set
- One mp3 per unique character
- Cache generated audio to avoid re-generating

## Stroke Order (Hanzi Writer)

Embedded in card HTML via CDN script. Each card includes:

```html
<script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script>
<div id="stroke-target"></div>
<script>
var writer = HanziWriter.create('stroke-target', '{{Character}}', {
  width: 150, height: 150, padding: 5,
  showOutline: true, strokeAnimationSpeed: 1,
  delayBetweenStrokes: 300
});
document.getElementById('stroke-target').addEventListener('click', function() {
  writer.animateCharacter();
});
</script>
```

**Important**: Anki cards run in a webview. Hanzi Writer loads character data from the jsdelivr CDN by default, which requires internet. For offline use, character data would need to be bundled.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Set Azure Speech credentials (required for high-quality audio)
export AZURE_SPEECH_KEY=your-key
export AZURE_SPEECH_REGION=eastus

# Generate all decks
python -m src.generate_deck

# Generate a specific lesson
python -m src.generate_deck --lesson 1

# Run tests
pytest tests/

# Extract characters from a photo of a textbook table
python -m src.extract_table photo.jpg --lesson 2

# Extract and auto-enrich with radicals, compounds, examples
python -m src.extract_table photo.jpg --lesson 2 --enrich

# Multiple images for one lesson
python -m src.extract_table page1.jpg page2.jpg --lesson 2
```

## Style & Conventions

- Python 3.10+
- Use type hints everywhere
- Use pathlib for file paths
- Keep character data in JSON files under `data/lessons/`
- All generated output goes to `output/` (gitignored)
- Model IDs and Deck IDs are hardcoded constants (never regenerate)
- Note GUIDs are based on character + lesson for stable updates

## Stable IDs (do not change)

```python
MODEL_ID = 1607392319      # genanki model ID for CPR character cards
DECK_ID_BASE = 2059400110  # base deck ID; per-lesson decks add lesson number
```

## Development Workflow

1. Add/edit character data in `data/lessons/lesson_XX.json`
2. Run `python -m src.generate_deck` to regenerate decks
3. Import `.apkg` files into Anki (File → Import)
4. Cards with matching GUIDs will update in place

## Known Constraints

- Azure Speech requires an Azure account + Speech resource (free tier: 500K chars/month)
- Falls back to gTTS (lower quality) when Azure credentials not configured
- Hanzi Writer CDN also requires internet for stroke data
- Some rare characters may not have stroke data in hanzi-writer-data
- Anki's webview may have JS limitations on some platforms
