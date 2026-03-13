"""Extract character data from photos of CPR textbook tables via vision APIs.

Supports Azure Document Intelligence (structured table extraction),
Azure OpenAI (cloud), Gemini (cloud), and Ollama (local) backends.
Backend priority: Azure DI > Azure AI > Gemini > Ollama.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
from pathlib import Path

import requests
from PIL import Image, ImageOps

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "lessons"

# Azure OpenAI config (set AZURE_AI_ENDPOINT and AZURE_AI_KEY env vars)

# Gemini config
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Ollama config (local fallback)
OLLAMA_BASE = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2-vision"

EXTRACT_PROMPT = """\
Look at this photo of a Chinese textbook vocabulary table. Extract each row as JSON.

Table layout: Each row has these columns (left to right):
  row number | pinyin | Chinese character(s) | word type (N/V/Adv/etc.) | English definition | Chinese example words/phrases

The LAST column is critical — it contains Chinese example words or phrases. Many rows have 2–3 examples separated by commas or spaces. Read this column carefully for EVERY row.

IMPORTANT — avoid cross-contamination:
- Rows have alternating background colors (light blue and yellowish). Each colored band is ONE row.
- Each row's examples appear ONLY within that row's colored band.
- Do NOT assign examples from one row to a different row.
- If a row has NO Chinese text in the rightmost column, its compounds list must be [].
- Many rows have no examples at all — that is normal. Only include examples you can see within THAT row's colored band.

Rules:
- The table has about 10-20 rows. Extract each row ONCE. Do NOT repeat entries.
- Stop after the last row. Do NOT continue generating.
- The orange header says "New Words" (main) or "Supplementary New Words" (supplementary).
- For EACH row, look at the rightmost column ON THAT ROW ONLY and extract ALL Chinese example words/phrases shown there.
- Do NOT mix examples into the English definition field.
- For proper names (PN), leave compounds empty.
- Some entries share a single row number (e.g. 请问, 请, and 问 share one number). These are SEPARATE entries — extract each one individually. Each sub-entry may have its own examples.
- The header may contain a reference number like "02-01-3". Extract it as "table_ref".
- If there is NO orange header and NO reference number, set "table_ref" to null and "section" to null (this means the table is a continuation of a previous table).

Return ONLY this JSON (no other text):
{"table_ref": "02-01-3", "section": "main", "entries": [{"character": "认识", "pinyin": "rènshi", "word_type": "V", "english": "to know; to recognize", "compounds": ["认识你", "认识他"]}]}

The "compounds" field must list ONLY the Chinese example words/phrases visible on that specific row's rightmost column. If a row has no examples, use [].
"""

ENRICH_PROMPT = """\
You are a Chinese language expert. For the character "{character}" ({pinyin} - {english}), provide:

1. "pinyin": the correct pinyin with tone marks for this character/word (e.g. "nǐ")
2. "radical": the radical of this character (e.g. 亻). For multi-character words, use the radical of the first character.
3. "radical_pinyin": the pinyin of the radical (e.g. rén)
4. "components": list of structural components (e.g. ["亻", "尔"]). For multi-character words, list components of the first character.
5. "compounds": exactly 3 common compound words using this character, each with:
   - "chinese": the compound word
   - "pinyin": pinyin with tone marks
   - "english": English translation
6. "textbook_translations": translations for these specific phrases: {textbook_compounds}
   For each phrase, provide pinyin and English. If the list is empty, return an empty object.
7. "example_sentence": a simple example sentence in Chinese using this character
8. "example_pinyin": pinyin of the example sentence
9. "example_english": English translation of the example sentence

Return ONLY valid JSON, no other text:
{{{{
  "pinyin": "nǐ",
  "radical": "亻",
  "radical_pinyin": "rén",
  "components": ["亻", "尔"],
  "compounds": [
    {{{{"chinese": "你好", "pinyin": "nǐ hǎo", "english": "hello"}}}}
  ],
  "textbook_translations": {{{{
    "认识你": {{{{"pinyin": "rènshi nǐ", "english": "to know you"}}}},
    "认识他": {{{{"pinyin": "rènshi tā", "english": "to know him"}}}}
  }}}},
  "example_sentence": "你叫什么名字？",
  "example_pinyin": "Nǐ jiào shénme míngzi?",
  "example_english": "What is your name?"
}}}}
"""


def _get_backend() -> str:
    """Determine which vision backend to use based on environment."""
    if os.environ.get("AZURE_DI_ENDPOINT") and os.environ.get("AZURE_DI_KEY"):
        return "azure_di"
    if os.environ.get("AZURE_AI_ENDPOINT") and os.environ.get("AZURE_AI_KEY"):
        return "azure_ai"
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return "ollama"


def check_ollama(model: str = DEFAULT_OLLAMA_MODEL) -> bool:
    """Check if Ollama is running and the model is available."""
    try:
        resp = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return any(model in m for m in models)
    except (requests.ConnectionError, requests.Timeout):
        return False


def encode_image(image_path: Path, max_dimension: int = 2048) -> str:
    """Read, apply EXIF rotation, resize, and base64-encode an image file."""
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)

    # Resize if larger than max_dimension on any side
    w, h = img.size
    if max(w, h) > max_dimension:
        scale = max_dimension / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        print(f"  Resized {w}x{h} → {new_w}x{new_h}")

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def extract_from_image(image_path: Path, model: str | None = None) -> dict:
    """Send an image to a vision model and extract character data.

    Backend priority: Azure AI Foundry > Gemini > Ollama.

    Returns:
        Dict with "section" and "entries" list.
    """
    backend = _get_backend()
    if backend == "azure_di":
        return _extract_azure_di(image_path)
    if backend == "azure_ai":
        return _extract_azure_ai(image_path)
    if backend == "gemini":
        return _extract_gemini(image_path)
    return _extract_ollama(image_path, model or DEFAULT_OLLAMA_MODEL)


def _extract_azure_di(image_path: Path) -> dict:
    """Extract character data using Azure Document Intelligence Layout API.

    Sends the image to the prebuilt-layout model which returns structured
    table data with explicit row/column cell indices, eliminating
    cross-contamination between rows.
    """
    endpoint = os.environ["AZURE_DI_ENDPOINT"].rstrip("/")
    api_key = os.environ["AZURE_DI_KEY"]

    # Read raw image bytes (no resizing — DI handles its own processing)
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    image_bytes = buf.getvalue()

    analyze_url = (
        f"{endpoint}/documentintelligence/documentModels/prebuilt-layout:analyze"
        f"?api-version=2024-11-30"
    )

    print("  Sending to Azure Document Intelligence...", end=" ", flush=True)
    for attempt in range(3):
        resp = requests.post(
            analyze_url,
            headers={
                "Ocp-Apim-Subscription-Key": api_key,
                "Content-Type": "application/octet-stream",
            },
            data=image_bytes,
            timeout=60,
        )
        if resp.status_code == 429:
            wait = int(resp.headers.get("Retry-After", 15))
            print(f"rate limited, waiting {wait}s...", end=" ", flush=True)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        break
    else:
        resp.raise_for_status()  # raise last 429

    # Poll for results
    operation_url = resp.headers["Operation-Location"]
    for _ in range(90):  # up to 90s
        time.sleep(1)
        poll = requests.get(
            operation_url,
            headers={"Ocp-Apim-Subscription-Key": api_key},
            timeout=30,
        )
        if poll.status_code == 429:
            time.sleep(int(poll.headers.get("Retry-After", 10)))
            continue
        poll.raise_for_status()
        status = poll.json().get("status")
        if status == "succeeded":
            print("done")
            return _parse_di_tables(poll.json()["analyzeResult"])
        if status == "failed":
            raise RuntimeError(f"Document Intelligence analysis failed: {poll.json()}")
        print(".", end="", flush=True)

    raise TimeoutError("Document Intelligence analysis timed out")


def _parse_di_tables(result: dict) -> dict:
    """Parse Document Intelligence Layout result into metadata + raw rows.

    DI provides structured cell data. We extract:
      - table_ref and section from headers/paragraphs
      - raw row strings (all cells concatenated per row)
    Then Gemini normalizes the raw rows into structured entries.
    """
    import re as _re

    tables = result.get("tables", [])
    if not tables:
        print("  Warning: No tables found in document")
        return {"table_ref": None, "section": None, "entries": []}

    raw_rows = []
    table_ref = None
    section = None

    for table in tables:
        rows: dict[int, dict[int, str]] = {}
        row_spans: dict[int, dict[int, int]] = {}
        for cell in table.get("cells", []):
            r = cell["rowIndex"]
            c = cell["columnIndex"]
            content = cell.get("content", "").strip()
            rows.setdefault(r, {})[c] = content
            row_spans.setdefault(r, {})[c] = cell.get("columnSpan", 1)

        if not rows:
            continue

        num_cols = table.get("columnCount", len(rows.get(0, {})))
        print(f"  Table: {table.get('rowCount', '?')} rows x {num_cols} cols")

        # Check if row 0 is a spanning header
        row0_spans = row_spans.get(0, {})
        is_header_row = any(span >= num_cols for span in row0_spans.values())

        # Extract metadata from header text
        header_text = " ".join(rows.get(0, {}).values())
        ref_match = _re.search(r'\d{1,2}-\d{2}-\d+', header_text)
        if ref_match:
            table_ref = ref_match.group()
        if "Supplementary" in header_text or "补充" in header_text:
            section = "supplementary"
        elif "New Words" in header_text or "生词" in header_text:
            section = "main"

        # Collect raw row strings (skip header if it spans all cols)
        start_row = 1 if is_header_row else 0
        for row_idx in sorted(rows.keys()):
            if row_idx < start_row:
                continue
            row = rows[row_idx]
            # Concatenate cells in column order with " | " separator
            cell_texts = [row[c] for c in sorted(row.keys())]
            raw_rows.append(" | ".join(cell_texts))

    # Fallback: detect section/ref from paragraphs
    if not section or not table_ref:
        content_text = ""
        for para in result.get("paragraphs", []):
            content_text += para.get("content", "") + " "
        if not section:
            if "Supplementary" in content_text or "补充" in content_text:
                section = "supplementary"
            elif "New Words" in content_text or "生词" in content_text:
                section = "main"
        if not table_ref:
            ref_match = _re.search(r'\d{1,2}-\d{2}-\d+', content_text)
            if ref_match:
                table_ref = ref_match.group()

    # Normalize raw rows via Gemini
    entries = _normalize_rows_gemini(raw_rows) if raw_rows else []

    return {
        "table_ref": table_ref,
        "section": section,
        "entries": entries,
    }


NORMALIZE_PROMPT = """\
You are parsing raw OCR rows from a Chinese textbook vocabulary table.
Each row was extracted by a document scanner. The cells within each row are separated by " | ".

The rows may have different column layouts (3, 4, or 5 columns). The data in each row always contains:
- A row number (e.g. "1.")
- Pinyin romanization (may have OCR errors like "ní" instead of "nǐ", or ":selected:" noise)
- Chinese character(s) (e.g. "你", "认识", "马大为")
- Word type (V, N, A, Adv, Pr, QPr, QPt, PN, Num, M, Conj, Prep, IE, MdPt, OpPt)
- English definition
- Optionally: Chinese example compounds/phrases at the end of the English field

For each row, extract:
- "character": the Chinese character(s)
- "pinyin": correct pinyin with tone marks (fix any OCR errors)
- "word_type": the word type abbreviation
- "english": the English definition only (no Chinese text)
- "compounds": list of Chinese example phrases (may appear after the English, or may be empty)

Ignore any ":selected:" or ":unselected:" noise in the data.
If a row is empty or contains only a row number, skip it.

Rows:
{rows}

Return ONLY a JSON array of objects, no other text.
"""


def _normalize_rows_gemini(raw_rows: list[str]) -> list[dict]:
    """Send raw DI row strings to Gemini for normalization into structured entries."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY required for DI row normalization")

    numbered_rows = "\n".join(f"Row {i+1}: {row}" for i, row in enumerate(raw_rows))
    prompt = NORMALIZE_PROMPT.format(rows=numbered_rows)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }

    print("  Normalizing rows via Gemini...", end=" ", flush=True)
    resp = requests.post(
        f"{GEMINI_API_URL}?key={api_key}",
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    print("done")

    entries = _parse_json_response(content)
    if isinstance(entries, dict) and "entries" in entries:
        entries = entries["entries"]
    if not isinstance(entries, list):
        raise ValueError(f"Expected list from Gemini, got {type(entries).__name__}")

    return [e for e in entries if e.get("character")]


def _extract_gemini(image_path: Path) -> dict:
    """Extract character data using Google Gemini vision API."""
    api_key = os.environ["GEMINI_API_KEY"]
    image_b64 = encode_image(image_path)

    payload = {
        "contents": [{
            "parts": [
                {"text": EXTRACT_PROMPT},
                {"inline_data": {"mime_type": "image/jpeg", "data": image_b64}},
            ]
        }],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 2048,
        },
    }

    print("  Sending to Gemini...", end=" ", flush=True)
    resp = requests.post(
        f"{GEMINI_API_URL}?key={api_key}",
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()

    content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    print("done")

    result = _parse_json_response(content)
    return _deduplicate_entries(result)


def _extract_azure_ai(image_path: Path) -> dict:
    """Extract character data using Azure AI Foundry (e.g. Phi-4 multimodal)."""
    endpoint = os.environ["AZURE_AI_ENDPOINT"].rstrip("/")
    api_key = os.environ["AZURE_AI_KEY"]
    image_b64 = encode_image(image_path)

    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": EXTRACT_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        },
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 2048,
    }

    print("  Sending to Azure AI...", end=" ", flush=True)
    resp = requests.post(
        endpoint,
        headers={
            "api-key": api_key,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()

    content = resp.json()["choices"][0]["message"]["content"]
    print("done")

    result = _parse_json_response(content)
    return _deduplicate_entries(result)


def _extract_ollama(image_path: Path, model: str) -> dict:
    """Extract character data using local Ollama vision model."""
    image_b64 = encode_image(image_path)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": EXTRACT_PROMPT,
                "images": [image_b64],
            }
        ],
        "stream": True,
        "options": {
            "temperature": 0.1,
            "num_predict": 2048,
        },
    }

    resp = requests.post(
        f"{OLLAMA_BASE}/api/chat",
        json=payload,
        stream=True,
        timeout=600,
    )
    resp.raise_for_status()

    content = ""
    print("  Generating", end="", flush=True)
    for line in resp.iter_lines():
        if not line:
            continue
        chunk = json.loads(line)
        token = chunk.get("message", {}).get("content", "")
        content += token
        print(".", end="", flush=True)
        if chunk.get("done"):
            break
    print(" done")

    result = _parse_json_response(content)
    return _deduplicate_entries(result)


def _deduplicate_entries(result: dict) -> dict:
    """Remove duplicate entries from extraction results."""
    if "entries" in result:
        seen = set()
        unique = []
        for entry in result["entries"]:
            key = entry.get("character", "")
            if key and key not in seen:
                seen.add(key)
                unique.append(entry)
        result["entries"] = unique
    return result


def _parse_json_response(text: str) -> dict:
    """Extract JSON from LLM response text, handling markdown fences."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [l for l in lines[1:] if l.strip() != "```"]
        text = "\n".join(lines)
    return json.loads(text)


def enrich_character(character: str, pinyin: str, english: str,
                     textbook_compounds: list[str] | None = None,
                     model: str = DEFAULT_OLLAMA_MODEL) -> dict:
    """Use an LLM to generate radical, components, compounds, and examples.

    Backend priority: Gemini > Ollama.
    """
    tb_list = json.dumps(textbook_compounds or [], ensure_ascii=False)
    prompt = ENRICH_PROMPT.format(
        character=character, pinyin=pinyin, english=english,
        textbook_compounds=tb_list,
    )

    if os.environ.get("GEMINI_API_KEY"):
        return _enrich_gemini(prompt)
    return _enrich_ollama(prompt, model)


def _enrich_gemini(prompt: str) -> dict:
    """Enrich via Gemini API."""
    api_key = os.environ["GEMINI_API_KEY"]
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    resp = requests.post(
        f"{GEMINI_API_URL}?key={api_key}",
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_json_response(content)


def _enrich_ollama(prompt: str, model: str) -> dict:
    """Enrich via local Ollama."""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.1},
    }
    resp = requests.post(
        f"{OLLAMA_BASE}/api/chat",
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["message"]["content"]
    return _parse_json_response(content)


def _is_cjk(char: str) -> bool:
    """Check if a character is in the CJK Unified Ideographs block."""
    cp = ord(char)
    return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF


def validate_entry(entry: dict) -> list[str]:
    """Validate a single character entry. Returns list of issues."""
    issues = []
    char = entry.get("character", "")
    if not char:
        issues.append("Empty character field")
    elif len(char) == 1 and not _is_cjk(char):
        issues.append(f"'{char}' is not a CJK character")

    if not entry.get("pinyin"):
        issues.append(f"Missing pinyin for '{char}'")
    if not entry.get("english"):
        issues.append(f"Missing english for '{char}'")
    return issues


def display_extracted(data: dict) -> None:
    """Print extracted characters for user review."""
    print("\n--- Extracted Characters ---")

    if data.get("main"):
        print(f"\nMain characters ({len(data['main'])}):")
        for i, e in enumerate(data["main"], 1):
            compounds = e.get("compounds", [])
            cmp_str = f"  ex: {', '.join(compounds)}" if compounds else ""
            print(f"  {i}. {e['character']}  {e['pinyin']}  —  {e['english']}{cmp_str}")

    if data.get("supplementary"):
        print(f"\nSupplementary characters ({len(data['supplementary'])}):")
        for i, e in enumerate(data["supplementary"], 1):
            compounds = e.get("compounds", [])
            cmp_str = f"  ex: {', '.join(compounds)}" if compounds else ""
            print(f"  {i}. {e['character']}  {e['pinyin']}  —  {e['english']}{cmp_str}")

    # Show any validation issues
    all_issues = []
    for section in ("main", "supplementary"):
        for entry in data.get(section, []):
            issues = validate_entry(entry)
            if issues:
                all_issues.extend(issues)

    if all_issues:
        print("\n⚠ Validation warnings:")
        for issue in all_issues:
            print(f"  - {issue}")


def build_lesson_json(lesson_num: int, title: str, data: dict,
                      enrich: bool = False, model: str = DEFAULT_OLLAMA_MODEL) -> dict:
    """Build the full lesson JSON structure, optionally enriching each character."""
    lesson = {
        "lesson": lesson_num,
        "title": title,
        "characters": {"main": [], "supplementary": []},
    }

    for section in ("main", "supplementary"):
        for entry in data.get(section, []):
            # Convert extracted compound strings to dict format
            textbook_compounds = []
            for c in entry.get("compounds", []):
                if isinstance(c, str):
                    textbook_compounds.append(
                        {"chinese": c, "pinyin": "", "english": "", "source": "textbook"}
                    )
                elif isinstance(c, dict):
                    c.setdefault("source", "textbook")
                    textbook_compounds.append(c)

            char_data = {
                "character": entry["character"],
                "pinyin": entry["pinyin"],
                "english": entry["english"],
                "radical": "",
                "radical_pinyin": "",
                "components": [],
                "compounds": textbook_compounds,
                "example_sentence": "",
                "example_pinyin": "",
                "example_english": "",
            }

            if enrich:
                print(f"  Enriching {entry['character']}...", end=" ", flush=True)
                try:
                    # Pass textbook compound Chinese texts for translation
                    tb_chinese = [c["chinese"] for c in textbook_compounds]
                    extra = enrich_character(
                        entry["character"], entry["pinyin"], entry["english"],
                        textbook_compounds=tb_chinese,
                        model=model,
                    )
                    if not isinstance(extra, dict):
                        raise ValueError(f"Expected dict, got {type(extra).__name__}")

                    # Cross-check pinyin: prefer Gemini's corrected pinyin
                    corrected_pinyin = extra.get("pinyin", "")
                    if corrected_pinyin:
                        char_data["pinyin"] = corrected_pinyin

                    char_data["radical"] = extra.get("radical", "")
                    char_data["radical_pinyin"] = extra.get("radical_pinyin", "")
                    char_data["components"] = extra.get("components", [])

                    # Fill in textbook compound translations
                    tb_trans = extra.get("textbook_translations", {})
                    if isinstance(tb_trans, dict):
                        for tc in textbook_compounds:
                            trans = tb_trans.get(tc["chinese"], {})
                            if isinstance(trans, dict):
                                if not tc.get("pinyin") and trans.get("pinyin"):
                                    tc["pinyin"] = trans["pinyin"]
                                if not tc.get("english") and trans.get("english"):
                                    tc["english"] = trans["english"]

                    # Merge: textbook compounds first, then enriched (no duplicates)
                    tb_chars = {c["chinese"] for c in textbook_compounds}
                    for ec in extra.get("compounds", []):
                        if isinstance(ec, dict) and ec.get("chinese") not in tb_chars:
                            ec["source"] = "generated"
                            textbook_compounds.append(ec)
                    char_data["compounds"] = textbook_compounds
                    char_data["example_sentence"] = extra.get("example_sentence", "")
                    char_data["example_pinyin"] = extra.get("example_pinyin", "")
                    char_data["example_english"] = extra.get("example_english", "")
                    print("done")
                except (json.JSONDecodeError, requests.RequestException,
                        ValueError, AttributeError, KeyError, TypeError) as exc:
                    print(f"failed ({exc})")
                # Rate limit for Gemini free tier (15 req/min)
                if os.environ.get("GEMINI_API_KEY"):
                    time.sleep(1)

            lesson["characters"][section].append(char_data)

    return lesson


def merge_into_existing(existing_path: Path, new_data: dict) -> dict:
    """Merge new character data into an existing lesson JSON file.

    New characters are appended; existing characters (by character field) are skipped.
    """
    with open(existing_path, encoding="utf-8") as f:
        existing = json.load(f)

    for section in ("main", "supplementary"):
        existing_chars = {
            e["character"] for e in existing["characters"].get(section, [])
        }
        for entry in new_data["characters"].get(section, []):
            if entry["character"] not in existing_chars:
                existing["characters"][section].append(entry)
                print(f"  Added {entry['character']} to {section}")
            else:
                print(f"  Skipped {entry['character']} (already exists in {section})")

    return existing


def save_lesson(lesson_data: dict, lesson_num: int) -> Path:
    """Write lesson data to JSON file."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / f"lesson_{lesson_num:02d}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(lesson_data, f, ensure_ascii=False, indent=2)
    return filepath


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract character data from a photo of a CPR textbook table."
    )
    parser.add_argument(
        "image",
        nargs="+",
        help="Path to one or more image files of the character table.",
    )
    parser.add_argument(
        "--lesson", "-l",
        type=int,
        default=None,
        help="Lesson number (e.g. 2 for lesson_02.json). Auto-detected from table header if omitted.",
    )
    parser.add_argument(
        "--title", "-t",
        type=str,
        default="",
        help="Lesson title (e.g. '你好'). Required for new lessons.",
    )
    parser.add_argument(
        "--enrich", "-e",
        action="store_true",
        help="Use LLM to generate radical, components, compounds, and examples.",
    )
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=DEFAULT_OLLAMA_MODEL,
        help=f"Ollama model to use (default: {DEFAULT_OLLAMA_MODEL}).",
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt.",
    )
    args = parser.parse_args()

    # Check backend availability
    backend = _get_backend()
    if backend == "azure_di":
        print("Using Azure Document Intelligence (Layout)")
    elif backend == "azure_ai":
        print("Using Azure AI Foundry")
    elif backend == "gemini":
        print("Using Gemini vision API")
    elif not check_ollama(args.model):
        print(f"Error: Ollama is not running or '{args.model}' model not found.")
        print("Start Ollama with: ollama serve")
        print(f"Pull the model with: ollama pull {args.model}")
        print("Or set AZURE_AI_ENDPOINT + AZURE_AI_KEY, or GEMINI_API_KEY.")
        sys.exit(1)
    else:
        print(f"Using Ollama ({args.model})")

    # Extract from all provided images and merge results
    all_data: dict[str, list] = {"main": [], "supplementary": []}
    seen_chars: set[str] = set()
    last_section: str = "main"
    last_lesson: int | None = args.lesson

    for i, img_path_str in enumerate(args.image):
        img_path = Path(img_path_str)
        if not img_path.exists():
            print(f"Error: Image not found: {img_path}")
            sys.exit(1)

        # Rate limit for cloud APIs (5 req/min on Gemini free tier)
        if i > 0 and backend in ("gemini", "azure_ai"):
            print("  Waiting 15s (rate limit)...", flush=True)
            time.sleep(15)

        print(f"Extracting from {img_path.name}...")
        result = extract_from_image(img_path, model=args.model)

        # Parse table_ref to get lesson number (middle part of "02-01-3")
        table_ref = result.get("table_ref") or ""
        section = result.get("section")

        if table_ref:
            print(f"  Table ref: {table_ref}")
            parts = table_ref.split("-")
            if len(parts) >= 2:
                try:
                    detected_lesson = int(parts[1])
                    if not args.lesson:
                        last_lesson = detected_lesson
                        print(f"  Detected lesson: {detected_lesson}")
                except ValueError:
                    pass

        # Handle continuation tables (no header = inherit from previous)
        if section:
            last_section = section
            print(f"  Section: {section}")
        else:
            section = last_section
            print(f"  Section: {section} (continuation)")

        for entry in result.get("entries", []):
            char = entry.get("character", "")
            if char and char not in seen_chars:
                all_data[section].append(entry)
                seen_chars.add(char)

    # Display and validate
    display_extracted(all_data)

    # Confirm with user
    # Resolve lesson number
    lesson_num = args.lesson or last_lesson
    if not lesson_num:
        print("Error: Could not detect lesson number. Use --lesson to specify.")
        sys.exit(1)
    print(f"\nLesson: {lesson_num}")

    if not args.yes:
        print()
        response = input("Proceed with this data? [Y/n/e(dit)] ").strip().lower()
        if response == "n":
            print("Aborted.")
            sys.exit(0)
        elif response == "e":
            # Dump to temp file for manual editing
            tmp = Path(f"/tmp/cpr_lesson_{lesson_num:02d}_extract.json")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            print(f"Edit the file and re-run: {tmp}")
            sys.exit(0)

    # Build full lesson structure
    existing_path = DATA_DIR / f"lesson_{lesson_num:02d}.json"

    if existing_path.exists():
        print(f"\nMerging into existing {existing_path.name}...")
        lesson_json = build_lesson_json(
            lesson_num, "", all_data, enrich=args.enrich, model=args.model
        )
        final = merge_into_existing(existing_path, lesson_json)
    else:
        title = args.title
        if not title:
            title = input("Enter lesson title (e.g. 你好): ").strip()
        print("\nBuilding lesson data...")
        final = build_lesson_json(
            lesson_num, title, all_data, enrich=args.enrich, model=args.model
        )

    # Save
    filepath = save_lesson(final, lesson_num)
    print(f"\nSaved to {filepath}")

    total = len(final["characters"]["main"]) + len(final["characters"]["supplementary"])
    print(f"Total characters: {total} "
          f"({len(final['characters']['main'])} main, "
          f"{len(final['characters']['supplementary'])} supplementary)")

    if args.enrich:
        print("\nTip: Review the enriched data for accuracy — LLM output may need corrections.")
    else:
        print("\nTip: Run with --enrich to auto-generate radicals, compounds, and examples.")


if __name__ == "__main__":
    main()
