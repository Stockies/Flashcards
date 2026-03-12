"""Main entry point — generates Anki .apkg decks for CPR lessons."""

import argparse
from pathlib import Path

import genanki

from src.audio import char_to_filename, generate_audio_batch
from src.characters import CharacterEntry, LessonData, load_all_lessons, load_lesson
from src.models import DECK_ID_BASE, CPRNote, get_model
from src.stroke_order import stroke_order_html

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
MEDIA_DIR = OUTPUT_DIR / "media"


def build_note(entry: CharacterEntry, lesson_num: int, model: genanki.Model) -> CPRNote:
    """Create a genanki Note from a CharacterEntry."""
    audio_ref = f"[sound:{char_to_filename(entry.character)}]"
    stroke_html = stroke_order_html(entry.character)

    return CPRNote(
        model=model,
        fields=[
            entry.character,
            entry.pinyin,
            entry.english,
            audio_ref,
            stroke_html,
            entry.char_type,
            str(lesson_num),
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
