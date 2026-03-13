"""Tests for the table extraction module."""

import json

from src.extract_table import (
    _is_cjk,
    _parse_json_response,
    validate_entry,
)


def test_is_cjk():
    assert _is_cjk("你")
    assert _is_cjk("好")
    assert _is_cjk("龙")
    assert not _is_cjk("a")
    assert not _is_cjk("1")
    assert not _is_cjk("。")


def test_parse_json_response_plain():
    text = '{"main": [{"character": "你", "pinyin": "nǐ", "english": "you"}], "supplementary": []}'
    result = _parse_json_response(text)
    assert result["main"][0]["character"] == "你"
    assert result["supplementary"] == []


def test_parse_json_response_with_fences():
    text = '```json\n{"main": [], "supplementary": []}\n```'
    result = _parse_json_response(text)
    assert result["main"] == []


def test_parse_json_response_with_fences_no_lang():
    text = '```\n{"main": [{"character": "好", "pinyin": "hǎo", "english": "good"}], "supplementary": []}\n```'
    result = _parse_json_response(text)
    assert result["main"][0]["character"] == "好"


def test_validate_entry_valid():
    entry = {"character": "你", "pinyin": "nǐ", "english": "you"}
    assert validate_entry(entry) == []


def test_validate_entry_missing_fields():
    issues = validate_entry({"character": "你", "pinyin": "", "english": ""})
    assert len(issues) == 2
    assert any("pinyin" in i for i in issues)
    assert any("english" in i for i in issues)


def test_validate_entry_non_cjk():
    issues = validate_entry({"character": "a", "pinyin": "a", "english": "a"})
    assert any("not a CJK" in i for i in issues)


def test_validate_entry_multi_char():
    # Multi-character words are now valid (e.g. compound words from CPR tables)
    issues = validate_entry({"character": "你好", "pinyin": "nǐhǎo", "english": "hello"})
    assert issues == []
