"""Load character data from lesson JSON files."""

import json
from dataclasses import dataclass, field
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "lessons"


@dataclass
class CompoundWord:
    """A compound word that uses the target character."""

    chinese: str
    pinyin: str
    english: str
    source: str = ""  # "textbook" or "generated"


@dataclass
class CharacterEntry:
    """A single character with its metadata."""

    character: str
    pinyin: str
    english: str
    char_type: str  # "main" or "supplementary"
    radical: str = ""
    radical_pinyin: str = ""
    components: list[str] = field(default_factory=list)
    compounds: list[CompoundWord] = field(default_factory=list)
    example_sentence: str = ""
    example_pinyin: str = ""
    example_english: str = ""


@dataclass
class LessonData:
    """All characters for a single lesson."""

    lesson: int
    title: str
    characters: list[CharacterEntry]


def load_lesson(lesson_num: int) -> LessonData:
    """Load character data for a specific lesson from its JSON file.

    Args:
        lesson_num: The lesson number (e.g. 1 for lesson_01.json).

    Returns:
        LessonData with all main and supplementary characters.

    Raises:
        FileNotFoundError: If the lesson JSON file doesn't exist.
    """
    filepath = DATA_DIR / f"lesson_{lesson_num:02d}.json"
    if not filepath.exists():
        raise FileNotFoundError(f"No data file for lesson {lesson_num}: {filepath}")

    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    characters: list[CharacterEntry] = []

    for entry in data["characters"].get("main", []):
        characters.append(
            CharacterEntry(
                character=entry["character"],
                pinyin=entry["pinyin"],
                english=entry["english"],
                char_type="main",
                radical=entry.get("radical", ""),
                radical_pinyin=entry.get("radical_pinyin", ""),
                components=entry.get("components", []),
                compounds=[
                    CompoundWord(
                        chinese=c["chinese"],
                        pinyin=c.get("pinyin", ""),
                        english=c.get("english", ""),
                        source=c.get("source", ""),
                    )
                    for c in entry.get("compounds", [])
                ],
                example_sentence=entry.get("example_sentence", ""),
                example_pinyin=entry.get("example_pinyin", ""),
                example_english=entry.get("example_english", ""),
            )
        )

    for entry in data["characters"].get("supplementary", []):
        characters.append(
            CharacterEntry(
                character=entry["character"],
                pinyin=entry["pinyin"],
                english=entry["english"],
                char_type="supplementary",
                radical=entry.get("radical", ""),
                radical_pinyin=entry.get("radical_pinyin", ""),
                components=entry.get("components", []),
                compounds=[
                    CompoundWord(
                        chinese=c["chinese"],
                        pinyin=c.get("pinyin", ""),
                        english=c.get("english", ""),
                        source=c.get("source", ""),
                    )
                    for c in entry.get("compounds", [])
                ],
                example_sentence=entry.get("example_sentence", ""),
                example_pinyin=entry.get("example_pinyin", ""),
                example_english=entry.get("example_english", ""),
            )
        )

    return LessonData(
        lesson=data["lesson"],
        title=data.get("title", ""),
        characters=characters,
    )


def load_all_lessons() -> list[LessonData]:
    """Load all available lesson data files.

    Returns:
        List of LessonData sorted by lesson number.
    """
    lessons: list[LessonData] = []
    for filepath in sorted(DATA_DIR.glob("lesson_*.json")):
        stem = filepath.stem  # e.g. "lesson_01"
        lesson_num = int(stem.split("_")[1])
        lessons.append(load_lesson(lesson_num))
    return lessons
