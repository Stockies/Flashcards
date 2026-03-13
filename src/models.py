"""Anki model and note definitions for CPR flashcards."""

from __future__ import annotations

from pathlib import Path

import genanki

# Stable IDs — do not change once decks have been imported into Anki
MODEL_ID = 1607392319
DECK_ID_BASE = 2059400110

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def _read_template(name: str) -> str:
    """Read an HTML or CSS template file from the templates/ directory."""
    return (TEMPLATES_DIR / name).read_text(encoding="utf-8")


def get_model() -> genanki.Model:
    """Create the genanki Model for CPR character cards.

    Fields:
        Character — the Chinese character
        Pinyin — romanization with tone marks
        English — English definition
        Audio — [sound:filename.mp3] reference
        StrokeOrder — HTML/JS for progressive stroke building display
        CharacterType — "main" or "supplementary"
        Lesson — lesson number
        Radical — radical with pinyin, e.g. "亻 (rén)"
        Components — character components, e.g. "亻 + 尔"
        CompoundsFront — HTML numbered list of compound words (Chinese only)
        CompoundsBack — HTML numbered list with pinyin and English
        ExampleSentence — example sentence in Chinese
        ExamplePinyin — pinyin for the example sentence
        ExampleEnglish — English translation of example sentence
    """
    return genanki.Model(
        MODEL_ID,
        "CPR Character",
        fields=[
            {"name": "Character"},
            {"name": "Pinyin"},
            {"name": "English"},
            {"name": "Audio"},
            {"name": "StrokeOrder"},
            {"name": "CharacterType"},
            {"name": "Lesson"},
            {"name": "Radical"},
            {"name": "Components"},
            {"name": "CompoundsFront"},
            {"name": "CompoundsBack"},
            {"name": "ExampleSentence"},
            {"name": "ExamplePinyin"},
            {"name": "ExampleEnglish"},
        ],
        templates=[
            {
                "name": "Recognition (Char → English)",
                "qfmt": _read_template("recognition_front.html"),
                "afmt": _read_template("recognition_back.html"),
            },
            {
                "name": "Recall (English → Char)",
                "qfmt": _read_template("recall_front.html"),
                "afmt": _read_template("recall_back.html"),
            },
        ],
        css=_read_template("card.css"),
    )


class CPRNote(genanki.Note):
    """Custom Note subclass with stable GUID based on character + lesson."""

    @property
    def guid(self) -> str:
        return genanki.guid_for(self.fields[0], self.fields[6])  # Character + Lesson
