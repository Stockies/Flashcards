"""Main entry point — generates Anki .apkg decks for CPR lessons."""

import argparse
from pathlib import Path

import genanki

from src.audio import char_to_filename, generate_audio_batch
from src.characters import CharacterEntry, CompoundWord, LessonData, load_all_lessons, load_lesson
from src.models import DECK_ID_BASE, CPRNote, get_model
from src.stroke_order import stroke_order_html

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MEDIA_DIR = OUTPUT_DIR / "media"


def format_radical(radical: str, radical_pinyin: str) -> str:
    """Format radical display, e.g. '亻 (rén)'."""
    if radical and radical_pinyin:
        return f"{radical} ({radical_pinyin})"
    return radical


def format_components(components: list[str]) -> str:
    """Format components display, e.g. '亻 + 尔'."""
    return " + ".join(components) if components else ""


def format_compounds_front(compounds: list[CompoundWord]) -> str:
    """Format compound words as a numbered list (Chinese characters only)."""
    if not compounds:
        return ""
    items = "".join(f"<li>{c.chinese}</li>" for c in compounds)
    return f"<ol>{items}</ol>"


def format_compounds_back(compounds: list[CompoundWord]) -> str:
    """Format compound words with pinyin and English translation."""
    if not compounds:
        return ""
    items = "".join(
        f'<li><span class="cmp-zh">{c.chinese}</span>'
        f'<span class="cmp-py">{c.pinyin}</span>'
        f'<span class="cmp-en">{c.english}</span></li>'
        for c in compounds
    )
    return f"<ol>{items}</ol>"


def build_note(entry: CharacterEntry, lesson_num: int, model: genanki.Model) -> CPRNote:
    """Create a genanki Note from a CharacterEntry."""
    audio_ref = f"[sound:{char_to_filename(entry.character)}]"
    stroke_html = stroke_order_html(entry.character)

    return CPRNote(
        model=model,
        fields=[
            entry.character,                                # Character
            entry.pinyin,                                   # Pinyin
            entry.english,                                  # English
            audio_ref,                                      # Audio
            stroke_html,                                    # StrokeOrder
            entry.char_type,                                # CharacterType
            str(lesson_num),                                # Lesson
            format_radical(entry.radical, entry.radical_pinyin),  # Radical
            format_components(entry.components),            # Components
            format_compounds_front(entry.compounds),        # CompoundsFront
            format_compounds_back(entry.compounds),         # CompoundsBack
            entry.example_sentence,                         # ExampleSentence
            entry.example_pinyin,                           # ExamplePinyin
            entry.example_english,                          # ExampleEnglish
        ],
    )


def build_deck(lesson: LessonData, model: genanki.Model) -> genanki.Deck:
    """Build a genanki Deck for a single lesson."""
    deck_id = DECK_ID_BASE + lesson.lesson
    deck_name = f"CPR3::Lesson {lesson.lesson:02d} - {lesson.title}"
    deck = genanki.Deck(deck_id, deck_name)

    for entry in lesson.characters:
        note = build_note(entry, lesson.lesson, model)
        deck.add_note(note)

    return deck


def generate_lesson_package(lesson: LessonData, model: genanki.Model) -> Path:
    """Generate audio, build deck, and write .apkg for one lesson.

    Returns:
        Path to the generated .apkg file.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    # Generate audio for all characters in the lesson
    all_chars = [e.character for e in lesson.characters]
    audio_paths = generate_audio_batch(all_chars, MEDIA_DIR)

    # Build the deck
    deck = build_deck(lesson, model)

    # Create package with media
    pkg = genanki.Package(deck)
    pkg.media_files = [str(path) for path in audio_paths.values()]

    output_path = OUTPUT_DIR / f"cpr3_lesson_{lesson.lesson:02d}.apkg"
    pkg.write_to_file(str(output_path))
    print(f"✅ Generated: {output_path} ({len(lesson.characters)} characters)")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Anki decks for New Practical Chinese Reader 3rd Edition"
    )
    parser.add_argument(
        "--lesson",
        type=int,
        default=None,
        help="Generate deck for a specific lesson number. If omitted, generates all.",
    )
    args = parser.parse_args()

    model = get_model()

    if args.lesson is not None:
        lesson = load_lesson(args.lesson)
        generate_lesson_package(lesson, model)
    else:
        lessons = load_all_lessons()
        if not lessons:
            print("⚠️  No lesson data found in data/lessons/. Add lesson JSON files first.")
            return
        for lesson in lessons:
            generate_lesson_package(lesson, model)

    print("🎉 Done!")


if __name__ == "__main__":
    main()
