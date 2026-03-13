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
            format_radical(entry.radical, entry.radical_pinyin),  # Radical
            format_components(entry.components),            # Components
            format_compounds_front(entry.compounds),        # CompoundsFront
            format_compounds_back(entry.compounds),         # CompoundsBack
            entry.example_sentence,                         # ExampleSentence
            entry.example_pinyin,                           # ExamplePinyin
            entry.example_english,                          # ExampleEnglish
        ],
    )


def build_deck(lesson: LessonData, model: genanki.Model) -> list[genanki.Deck]:
    """Build genanki Decks for a single lesson, split by character type.

    Returns a list of decks:
      - CPR Book 1 3rd Edition::Lesson XX - Title::New Words
      - CPR Book 1 3rd Edition::Lesson XX - Title::Supplementary Words
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

    decks = [main_deck]
    if supp_deck.notes:
        decks.append(supp_deck)
    return decks


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

    # Build the decks (split by character type)
    decks = build_deck(lesson, model)

    # Create package with media
    pkg = genanki.Package(decks)
    pkg.media_files = [str(path) for path in audio_paths.values()]

    output_path = OUTPUT_DIR / f"cpr3_lesson_{lesson.lesson:02d}.apkg"
    pkg.write_to_file(str(output_path))
    main_count = sum(1 for e in lesson.characters if e.char_type != "supplementary")
    supp_count = sum(1 for e in lesson.characters if e.char_type == "supplementary")
    print(f"✅ Generated: {output_path} ({main_count} new + {supp_count} supplementary)")
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
