"""Basic smoke tests for deck generation."""

from pathlib import Path

from src.audio import char_to_filename
from src.characters import CharacterEntry, LessonData
from src.models import CPRNote, get_model
from src.stroke_order import stroke_order_html


def test_char_to_filename():
    assert char_to_filename("你") == "char_4F60.mp3"
    assert char_to_filename("好") == "char_597D.mp3"


def test_stroke_order_html_contains_character():
    html = stroke_order_html("你")
    assert "你" in html
    assert "HanziWriter" in html
    assert "hw-4F60" in html


def test_model_has_correct_fields():
    model = get_model()
    field_names = [f["name"] for f in model.fields]
    assert "Character" in field_names
    assert "Pinyin" in field_names
    assert "English" in field_names
    assert "Audio" in field_names
    assert "StrokeOrder" in field_names


def test_note_guid_stability():
    model = get_model()
    note1 = CPRNote(model=model, fields=["你", "nǐ", "you", "", "", "main", "1"])
    note2 = CPRNote(model=model, fields=["你", "nǐ", "you", "", "", "main", "1"])
    note3 = CPRNote(model=model, fields=["好", "hǎo", "good", "", "", "main", "1"])
    assert note1.guid == note2.guid  # same char + lesson → same GUID
    assert note1.guid != note3.guid  # different char → different GUID
