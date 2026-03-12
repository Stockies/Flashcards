# Chinese Practical Reader — Anki Flashcard Generator

Generate Anki-compatible flashcard decks (`.apkg`) for the **New Practical Chinese Reader (3rd Edition)**.

## Features

- 📝 All **main** and **supplementary** characters per lesson
- 🔊 Audio pronunciation for each character (via Google TTS)
- ✍️ Stroke order animation on each card (via [Hanzi Writer](https://hanziwriter.org/))
- 🔄 Two card types: **Recognition** (Chinese → English) and **Recall** (English → Chinese)
- 📦 Outputs `.apkg` files ready to import into Anki

## Quick Start

```bash
# Clone the repo
git clone https://github.com/Stockies/Flashcards.git
cd Flashcards

# Install dependencies
pip install -r requirements.txt

# Generate all lesson decks
python -m src.generate_deck

# Generate a single lesson
python -m src.generate_deck --lesson 1
```

Then import the `.apkg` files from `output/` into Anki via **File → Import**.

## How It Works

1. Character data is defined in JSON files under `data/lessons/`
2. Audio is generated per unique character using [gTTS](https://github.com/pndurette/gTTS) (Google Text-to-Speech)
3. Stroke order animations use [Hanzi Writer](https://hanziwriter.org/) embedded in the card HTML
4. Decks are assembled using [genanki](https://github.com/kerrickstaley/genanki) and written as `.apkg` packages

## Card Layout

### Front (Recognition)
- Large Chinese character
- Audio auto-plays

### Back (Recognition)
- Pinyin
- English definition
- Stroke order animation (click to play)

## Project Structure

```
├── src/               # Python source
│   ├── generate_deck.py   # Main entry point
│   ├── models.py          # Anki model/note definitions
│   ├── audio.py           # TTS audio generation
│   ├── stroke_order.py    # Hanzi Writer HTML generation
│   └── characters.py      # Character data loader
├── data/lessons/      # Character data per lesson (JSON)
├── templates/         # Card HTML templates
├── output/            # Generated .apkg files (gitignored)
└── tests/             # Tests
```

## Requirements

- Python 3.10+
- Internet connection (for gTTS and Hanzi Writer CDN)
- [Anki](https://apps.ankiweb.net/) to use the generated decks

## License

MIT
