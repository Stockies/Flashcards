# CLAUDE.md — Project Context for AI Assistants

## Project Overview

Generate Anki-compatible flashcard decks (`.apkg` files) for the **New Practical Chinese Reader (3rd Edition)**. Each lesson produces a deck containing **all main characters** and **all supplementary characters** with:

- Chinese character display
- Pinyin romanization
- English definition
- Stroke order animation (via Hanzi Writer)
- Audio pronunciation (via gTTS)

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
│   ├── audio.py           # gTTS wrapper — generates mp3 per character
│   ├── stroke_order.py    # Generates stroke order HTML using Hanzi Writer JS
│   └── characters.py      # Character data per lesson (source of truth)
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
| **gTTS** | Free TTS via Google Translate API — generates mp3 audio | https://github.com/pndurette/gTTS |
| **Hanzi Writer** | JS library for stroke order animations (embedded in card HTML) | https://hanziwriter.org/docs.html |
| **hanzi-writer-data** | Stroke data for all CJK characters | https://github.com/chanind/hanzi-writer-data |

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

## Audio Generation (gTTS)

```python
from gtts import gTTS
tts = gTTS('你', lang='zh-cn')
tts.save('char_4F60.mp3')
```

- Language code: `zh-cn` (Mandarin Chinese, simplified)
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

# Generate all decks
python -m src.generate_deck

# Generate a specific lesson
python -m src.generate_deck --lesson 1

# Run tests
pytest tests/
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

- gTTS requires internet access (uses Google Translate API)
- Hanzi Writer CDN also requires internet for stroke data
- Some rare characters may not have stroke data in hanzi-writer-data
- Google Translate TTS is undocumented/unofficial — may break
- Anki's webview may have JS limitations on some platforms
