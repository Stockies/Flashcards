"""Generate audio pronunciation files for Chinese characters using gTTS."""

from pathlib import Path

from gtts import gTTS


def char_to_filename(char: str) -> str:
    """Convert a character to a unique mp3 filename using its Unicode codepoint."""
    codepoint = f"{ord(char):04X}"
    return f"char_{codepoint}.mp3"


def generate_audio(char: str, output_dir: Path) -> Path:
    """Generate an mp3 file for a single Chinese character.

    Args:
        char: A single Chinese character.
        output_dir: Directory to save the mp3 file.

    Returns:
        Path to the generated mp3 file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = char_to_filename(char)
    filepath = output_dir / filename

    if filepath.exists():
        return filepath

    tts = gTTS(char, lang="zh-cn")
    tts.save(str(filepath))
    return filepath


def generate_audio_batch(characters: list[str], output_dir: Path) -> dict[str, Path]:
    """Generate audio for a list of characters, skipping already-generated ones.

    Args:
        characters: List of Chinese characters.
        output_dir: Directory to save mp3 files.

    Returns:
        Dict mapping character → mp3 file path.
    """
    results: dict[str, Path] = {}
    for char in characters:
        results[char] = generate_audio(char, output_dir)
    return results
