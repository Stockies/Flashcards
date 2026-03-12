"""Generate stroke order HTML snippets using Hanzi Writer (JS, loaded via CDN)."""


def stroke_order_html(character: str) -> str:
    """Generate HTML/JS snippet that renders a Hanzi Writer stroke order animation.

    The snippet creates a self-contained div with an inline script. Clicking the
    character area replays the stroke animation. The Hanzi Writer library and
    character data are loaded from the jsdelivr CDN.

    Args:
        character: A single Chinese character.

    Returns:
        HTML string to embed in an Anki card field.
    """
    # Use a unique ID per character to avoid collisions if multiple are on screen
    codepoint = f"{ord(character):04X}"
    target_id = f"hw-{codepoint}"

    return f"""<div id="{target_id}" style="margin:0 auto;"></div>
<script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3.5/dist/hanzi-writer.min.js"></script>
<script>
(function() {{
  if (typeof HanziWriter === 'undefined') return;
  var el = document.getElementById('{target_id}');
  if (!el) return;
  var writer = HanziWriter.create('{target_id}', '{character}', {{
    width: 150, height: 150, padding: 5,
    showOutline: true,
    strokeAnimationSpeed: 1,
    delayBetweenStrokes: 300
  }});
  el.style.cursor = 'pointer';
  el.addEventListener('click', function() {{ writer.animateCharacter(); }});
  writer.loopCharacterAnimation();
}})();
</script>"""
