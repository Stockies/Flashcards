"""Basic smoke tests for deck generation."""

from pathlib import Path

from src.audio import char_to_filename
from src.characters import CharacterEntry, CompoundWord, LessonData
from src.generate_deck import (
    format_components,
    format_compounds_back,
    format_compounds_front,
    format_radical,
)
from src.models import CPRNote, get_model
from src.stroke_order import stroke_order_html


def test_char_to_filename():
    assert char_to_filename("你") == "char_4F60.mp3"
    assert char_to_filename("好") == "char_597D.mp3"
    assert char_to_filename("请问") == "char_8BF7_95EE.mp3"


def test_stroke_order_html_contains_character():
    html = stroke_order_html("你")
    assert "你" in html
    assert "sp-4F60" in html
    assert "hanzi-writer-data" in html


def test_model_has_correct_fields():
    model = get_model()
    field_names = [f["name"] for f in model.fields]
    assert "Character" in field_names
    assert "Pinyin" in field_names
    assert "English" in field_names
    assert "Audio" in field_names
    assert "StrokeOrder" in field_names
    assert "Radical" in field_names
    assert "Components" in field_names
    assert "CompoundsFront" in field_names
    assert "CompoundsBack" in field_names
    assert "ExampleSentence" in field_names
    assert len(model.fields) == 16


def test_note_guid_stability():
    model = get_model()
    fields_14 = ["你", "nǐ", "you", "", "", "main", "1", "", "", "", "", "", "", "", "", ""]
    note1 = CPRNote(model=model, fields=list(fields_14))
    note2 = CPRNote(model=model, fields=list(fields_14))
    fields_14_diff = list(fields_14)
    fields_14_diff[0] = "好"
    note3 = CPRNote(model=model, fields=fields_14_diff)
    assert note1.guid == note2.guid  # same char + lesson → same GUID
    assert note1.guid != note3.guid  # different char → different GUID


def test_format_radical():
    assert format_radical("亻", "rén") == "亻 (rén)"
    assert format_radical("女", "") == "女"
    assert format_radical("", "") == ""


def test_format_components():
    assert format_components(["亻", "尔"]) == "亻 + 尔"
    assert format_components(["马"]) == "马"
    assert format_components([]) == ""


def test_format_compounds_front():
    compounds = [
        CompoundWord("你好", "nǐ hǎo", "hello", source="textbook"),
        CompoundWord("你们", "nǐ men", "you all", source="generated"),
    ]
    html = format_compounds_front(compounds)
    assert "<ol>" in html
    assert "你好" in html
    assert "你们" in html
    assert 'cmp-tb' in html  # textbook styling
    assert 'cmp-gen' in html  # generated styling
    assert "nǐ hǎo" not in html  # front should not show pinyin


def test_format_compounds_back():
    compounds = [
        CompoundWord("你好", "nǐ hǎo", "hello"),
    ]
    html = format_compounds_back(compounds)
    assert "<ol>" in html
    assert "你好" in html
    assert "nǐ hǎo" in html
    assert "hello" in html
