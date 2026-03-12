"""Anki model and note definitions for CPR flashcards."""

import genanki

# Stable IDs — do not change once decks have been imported into Anki
MODEL_ID = 1607392319
DECK_ID_BASE = 2059400110


def get_model() -> genanki.Model:
    """Create the genanki Model for CPR character cards.

    Fields:
        Character — the Chinese character
        Pinyin — romanization with tone marks
        English — English definition
        Audio — [sound:filename.mp3] reference
        StrokeOrder — HTML/JS for Hanzi Writer animation
        CharacterType — "main" or "supplementary"
        Lesson — lesson number
    """
    return genanki.Model(
        MODEL_ID,
        "CPR Character",
        fields=[
            {"name": "Character"},
            {"name": "Pinyin"},
            {"name": "English"},
            {"name": "Audio"},
            {"name": "StrokeOrder"},
            {"name": "CharacterType"},
            {"name": "Lesson"},
        ],
        templates=[
            {
                "name": "Recognition (Char → English)",
                "qfmt": """
<div class="card-front">
  <div class="character">{{Character}}</div>
  <div class="audio">{{Audio}}</div>
  <div class="badge {{CharacterType}}">{{CharacterType}}</div>
</div>
""",
                "afmt": """
<div class="card-back">
  <div class="character">{{Character}}</div>
  <div class="pinyin">{{Pinyin}}</div>
  <div class="english">{{English}}</div>
  <hr>
  <div class="stroke-order">{{StrokeOrder}}</div>
  <div class="audio">{{Audio}}</div>
</div>
""",
            },
            {
                "name": "Recall (English → Char)",
                "qfmt": """
<div class="card-front">
  <div class="english recall-prompt">{{English}}</div>
  <div class="pinyin hint">{{Pinyin}}</div>
</div>
""",
                "afmt": """
<div class="card-back">
  <div class="character">{{Character}}</div>
  <div class="pinyin">{{Pinyin}}</div>
  <div class="english">{{English}}</div>
  <hr>
  <div class="stroke-order">{{StrokeOrder}}</div>
  <div class="audio">{{Audio}}</div>
</div>
""",
            },
        ],
        css="""
.card {
  font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  text-align: center;
  padding: 20px;
  background: #fafafa;
}
.character {
  font-size: 72px;
  margin: 20px 0;
  color: #333;
}
.pinyin {
  font-size: 28px;
  color: #666;
  margin: 10px 0;
}
.english {
  font-size: 24px;
  color: #444;
  margin: 10px 0;
}
.recall-prompt {
  font-size: 32px;
  margin: 30px 0;
}
.hint {
  font-size: 20px;
  color: #999;
}
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  color: white;
  margin-top: 10px;
}
.badge.main { background: #4CAF50; }
.badge.supplementary { background: #FF9800; }
.stroke-order {
  margin: 15px auto;
  display: flex;
  justify-content: center;
}
hr {
  border: none;
  border-top: 1px solid #ddd;
  margin: 15px 0;
}
""",
    )


class CPRNote(genanki.Note):
    """Custom Note subclass with stable GUID based on character + lesson."""

    @property
    def guid(self) -> str:
        return genanki.guid_for(self.fields[0], self.fields[6])  # Character + Lesson
