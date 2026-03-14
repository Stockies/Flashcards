# CLAUDE.md — Project Context for AI Assistants

## Project Overview

Generate Anki-compatible flashcard decks (`.apkg` files) for the **New Practical Chinese Reader (3rd Edition)**. Two output packages are produced:

- `cpr3_new_words.apkg` — all lessons' New Words sub-decks
- `cpr3_supplementary_words.apkg` — all lessons' Supplementary Words sub-decks

Each card includes:

- Chinese character display
- Pinyin romanization
- English definition
- Word type (V, N, A, Adv, Pr, etc.)
- Stroke order display (progressive stroke building via Hanzi Writer data)
- Audio pronunciation (gTTS, with Azure Speech TTS as optional upgrade)
- Radical and component breakdown
- Compound words (textbook examples + AI-generated, visually distinguished)
- Example sentences
- Source table reference (e.g. "2-01-02")

## Architecture

```
Flashcards/
├── CLAUDE.md              # This file — AI context
├── README.md              # Project documentation
├── pyproject.toml         # Python project config (uv/pip)
├── requirements.txt       # Pinned dependencies
├── .env                   # API keys (gitignored)
├── src/
│   ├── __init__.py
│   ├── extract_table.py   # Single-pass image → lesson JSON pipeline (DI + Gemini)
│   ├── generate_deck.py   # Builds .apkg packages (new words + supplementary)
│   ├── models.py          # genanki Model/Note definitions (16 fields)
│   ├── audio.py           # TTS audio generation (Azure Speech / gTTS)
│   ├── stroke_order.py    # Generates stroke order HTML using Hanzi Writer data
│   └── characters.py      # CharacterEntry/CompoundWord dataclasses, JSON loading
├── data/
│   └── lessons/           # Per-lesson JSON character lists (enriched)
│       ├── lesson_01.json
│       └── ...lesson_10.json
├── input/                 # Textbook photos for extraction (gitignored)
├── output/                # Generated .apkg files (gitignored)
│   └── media/             # Generated mp3 files (gitignored)
├── templates/
│   ├── card.css           # Shared card CSS
│   ├── recognition_front.html  # Character → English card front
│   └── recognition_back.html   # Character → English card back
└── tests/
    └── test_generate.py        # Deck generation tests
```

### Extraction Pipeline (single-pass, multi-lesson)

1. **All images** are processed in one invocation — lesson numbers are auto-detected from `table_ref` headers (e.g. `"2-01-02"` → lesson 1)
2. **Azure Document Intelligence** (Layout API) extracts structured table cells from textbook photos — isolates rows to prevent cross-contamination between entries
3. **Gemini 2.5 Flash** normalizes raw DI rows into structured entries (character, pinyin, word_type, english, compounds) and corrects OCR pinyin errors
4. **Gemini 2.5 Flash** enriches each character with radicals, components, compound words, and example sentences
5. **Multi-char decomposition** splits words like 认识 into individual character cards. Cross-lesson dedup prevents decomposed characters from repeating if already covered in earlier lessons. Non-CJK characters (e.g. "T" from "T恤") are skipped during decomposition.

### Deck Hierarchy

Two separate `.apkg` packages, each containing per-lesson sub-decks:

```
# cpr3_new_words.apkg
CPR Book 1 3rd Edition::Lesson 01 - 你好::New Words
CPR Book 1 3rd Edition::Lesson 02 - ...::New Words
...

# cpr3_supplementary_words.apkg
CPR Book 1 3rd Edition::Lesson 01 - 你好::Supplementary Words
CPR Book 1 3rd Edition::Lesson 02 - ...::Supplementary Words
...
```

## Key Technologies

| Tool | Purpose |
|------|---------|
| **genanki** | Python library for generating `.apkg` Anki decks |
| **Azure Document Intelligence** | Structured table extraction from photos (prebuilt-layout model) |
| **Gemini 2.5 Flash** | Row normalization, pinyin correction, and character enrichment |
| **gTTS** | Free TTS audio (default) |
| **Azure Speech** | Neural TTS upgrade (optional, `zh-CN-XiaoxiaoNeural` voice) |
| **Hanzi Writer** | Stroke data for progressive stroke building display |

## Model Fields (16 total)

1. `Character` — the Chinese character (e.g. 你)
2. `Pinyin` — romanization with tone marks (e.g. nǐ)
3. `English` — definition (e.g. you)
4. `Audio` — `[sound:char_XXXX.mp3]` reference
5. `StrokeOrder` — HTML/SVG for progressive stroke building display
6. `CharacterType` — "main" or "supplementary"
7. `Lesson` — lesson number
8. `WordType` — word type abbreviation (V, N, A, Adv, Pr, etc.)
9. `TableRef` — source table reference (e.g. "2-01-02")
10. `Radical` — radical with pinyin, e.g. "亻 (rén)"
11. `Components` — structural parts, e.g. "亻 + 尔"
12. `CompoundsFront` — HTML list of compound words (Chinese only)
13. `CompoundsBack` — HTML list with pinyin and English
14. `ExampleSentence` — example sentence in Chinese
15. `ExamplePinyin` — pinyin for the example sentence
16. `ExampleEnglish` — English translation of example sentence

### Card Template

**Recognition only** (Chinese → English): Front shows Character + Compounds, Back shows Pinyin + English + Audio + StrokeOrder + Source + Examples.

### Compound Word Styling

- **Textbook compounds** (from DI extraction): blue left border (`cmp-tb`)
- **Generated compounds** (from Gemini enrichment): gray left border (`cmp-gen`)

## Character Data Format (per lesson JSON)

```json
{
  "lesson": 1,
  "title": "Lesson 1",
  "characters": {
    "main": [
      {
        "character": "认识",
        "pinyin": "rènshi",
        "english": "to know; to recognize",
        "word_type": "V",
        "table_ref": "2-01-02",
        "radical": "讠",
        "radical_pinyin": "yán",
        "components": ["讠", "刃"],
        "compounds": [
          {"chinese": "认识你", "pinyin": "rènshi nǐ", "english": "to know you", "source": "textbook"},
          {"chinese": "认真", "pinyin": "rènzhēn", "english": "earnest; serious", "source": "generated"}
        ],
        "example_sentence": "我认识他。",
        "example_pinyin": "Wǒ rènshi tā.",
        "example_english": "I know him."
      }
    ],
    "supplementary": [...]
  }
}
```

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Generate both .apkg packages (new words + supplementary)
python -m src.generate_deck

# Run tests
pytest tests/

# Extract all lessons from textbook photos (single-pass, auto-detect lessons)
python -m src.extract_table input/*.jpeg --enrich --yes

# Extract with custom lesson titles
python -m src.extract_table input/*.jpeg --titles "你好,你是哪国人,..." --enrich

# Extract without enrichment (faster, for testing)
python -m src.extract_table input/*.jpeg --yes
```

## Environment Variables

```bash
# Required for extraction
AZURE_DI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DI_KEY=your-key

# Required for normalization and enrichment
GEMINI_API_KEY=your-key

# Optional: high-quality audio (falls back to gTTS)
AZURE_SPEECH_KEY=your-key
AZURE_SPEECH_REGION=eastus
```

## Stable IDs (do not change)

```python
MODEL_ID = 1607392319      # genanki model ID for CPR character cards
DECK_ID_BASE = 2059400110  # base deck ID; per-lesson decks derive from this
```

## Style & Conventions

- Python 3.9+
- Use type hints everywhere (use `typing.Optional` not `X | None` for 3.9 compat)
- Use pathlib for file paths
- Keep character data in JSON files under `data/lessons/`
- All generated output goes to `output/` (gitignored)
- Input images go in `input/` (gitignored)
- Model IDs and Deck IDs are hardcoded constants (never regenerate)
- Note GUIDs are based on character + lesson for stable updates

## Development Workflow

1. Take photos of textbook vocabulary tables
2. Run `python -m src.extract_table input/*.jpeg --enrich --yes` to extract all lessons
3. Run `python -m src.generate_deck` to generate `.apkg` packages
4. Import into Anki (File → Import) — cards with matching GUIDs update in place
