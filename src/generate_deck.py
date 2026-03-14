"""Main entry point — generates Anki .apkg decks for CPR lessons."""

import argparse
from pathlib import Path
from typing import Optional

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
    items = ""
    for c in compounds:
        cls = "tb" if c.source == "textbook" else "gen"
        items += f'<li class="cmp-{cls}">{c.chinese}</li>'
    return f"<ol>{items}</ol>"


def format_compounds_back(compounds: list[CompoundWord]) -> str:
    """Format compound words with pinyin and English translation."""
    if not compounds:
        return ""
    items = ""
    for c in compounds:
        cls = "tb" if c.source == "textbook" else "gen"
        items += (
            f'<li class="cmp-{cls}"><span class="cmp-zh">{c.chinese}</span>'
            f'<span class="cmp-py">{c.pinyin}</span>'
            f'<span class="cmp-en">{c.english}</span></li>'
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
            entry.word_type,                                # WordType
            entry.table_ref,                                # TableRef
            format_radical(entry.radical, entry.radical_pinyin),  # Radical
            format_components(entry.components),            # Components
            format_compounds_front(entry.compounds),        # CompoundsFront
            format_compounds_back(entry.compounds),         # CompoundsBack
            entry.example_sentence,                         # ExampleSentence
            entry.example_pinyin,                           # ExamplePinyin
            entry.example_english,                          # ExampleEnglish
        ],
    )


def build_decks(lesson: LessonData, model: genanki.Model) -> tuple[genanki.Deck, Optional[genanki.Deck]]:
    """Build genanki Decks for a single lesson, split by character type.

    Returns:
        (main_deck, supp_deck_or_None)
    """
    base_name = f"CPR Book 1 3rd Edition::Lesson {lesson.lesson:02d} - {lesson.title}"

    main_deck_id = DECK_ID_BASE + lesson.lesson * 10 + 1
    supp_deck_id = DECK_ID_BASE + lesson.lesson * 10 + 2
    main_deck = genanki.Deck(main_deck_id, f"{base_name}::New Words")
    supp_deck = genanki.Deck(supp_deck_id, f"{base_name}::Supplementary Words")

    for entry in lesson.characters:
        note = build_note(entry, lesson.lesson, model)
        if entry.char_type == "supplementary":
            supp_deck.add_note(note)
        else:
            main_deck.add_note(note)

    return main_deck, supp_deck if supp_deck.notes else None


def generate_packages(lessons: list[LessonData], model: genanki.Model) -> list[Path]:
    """Generate two .apkg packages across all lessons.

    - cpr3_new_words.apkg: all lessons' New Words decks
    - cpr3_supplementary_words.apkg: all lessons' Supplementary Words decks

    Returns:
        List of output .apkg paths.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    main_decks: list[genanki.Deck] = []
    supp_decks: list[genanki.Deck] = []
    all_audio: dict[str, Path] = {}

    for lesson in lessons:
        # Generate audio for all characters in the lesson
        all_chars = [e.character for e in lesson.characters]
        audio_paths = generate_audio_batch(all_chars, MEDIA_DIR)
        all_audio.update(audio_paths)

        main_deck, supp_deck = build_decks(lesson, model)
        main_deck_count = len(main_deck.notes)
        supp_deck_count = len(supp_deck.notes) if supp_deck else 0
        print(f"  Lesson {lesson.lesson:02d}: {main_deck_count} new + {supp_deck_count} supplementary")

        main_decks.append(main_deck)
        if supp_deck:
            supp_decks.append(supp_deck)

    media_files = [str(path) for path in all_audio.values()]
    output_paths: list[Path] = []

    # New Words package
    main_pkg = genanki.Package(main_decks)
    main_pkg.media_files = media_files
    main_path = OUTPUT_DIR / "cpr3_new_words.apkg"
    main_pkg.write_to_file(str(main_path))
    total_main = sum(len(d.notes) for d in main_decks)
    print(f"✅ {main_path.name}: {total_main} cards across {len(main_decks)} lessons")
    output_paths.append(main_path)

    # Supplementary Words package
    if supp_decks:
        supp_pkg = genanki.Package(supp_decks)
        supp_pkg.media_files = media_files
        supp_path = OUTPUT_DIR / "cpr3_supplementary_words.apkg"
        supp_pkg.write_to_file(str(supp_path))
        total_supp = sum(len(d.notes) for d in supp_decks)
        print(f"✅ {supp_path.name}: {total_supp} cards across {len(supp_decks)} lessons")
        output_paths.append(supp_path)

    return output_paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate Anki decks for New Practical Chinese Reader 3rd Edition"
    )
    parser.add_argument(
        "--lesson",
        type=int,
        default=None,
        help="Generate decks for a specific lesson number. If omitted, generates all.",
    )
    args = parser.parse_args()

    model = get_model()

    if args.lesson is not None:
        lessons = [load_lesson(args.lesson)]
    else:
        lessons = load_all_lessons()

    if not lessons:
        print("⚠️  No lesson data found in data/lessons/. Add lesson JSON files first.")
        return

    generate_packages(lessons, model)

    print("🎉 Done!")


if __name__ == "__main__":
    main()
