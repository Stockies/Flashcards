"""Generate stroke order HTML snippets showing progressive stroke building.

Uses hanzi-writer-data from the jsdelivr CDN to fetch stroke SVG paths,
then renders a series of small boxes — each showing one more stroke completed.
"""


def stroke_order_html(character: str) -> str:
    """Generate HTML/JS that renders progressive stroke-building boxes.

    Each box shows the character outline with an increasing number of strokes
    filled in, from the first stroke alone to the complete character.

    For multi-character words, renders stroke order for each character
    in sequence.

    The stroke data is fetched from the hanzi-writer-data CDN at card display
    time and rendered as inline SVGs.

    Args:
        character: A Chinese character or multi-character word.

    Returns:
        HTML string to embed in an Anki card field.
    """
    if len(character) == 1:
        return _stroke_order_single(character)
    # Multi-character: render each character separately
    parts = []
    for ch in character:
        parts.append(_stroke_order_single(ch))
    return '<div class="stroke-multi">' + "".join(parts) + "</div>"


def _stroke_order_single(character: str) -> str:
    """Render stroke order for a single character."""
    codepoint = f"{ord(character):04X}"
    container_id = f"sp-{codepoint}"

    return f"""<div id="{container_id}" class="stroke-prog"></div>
<script>
(function() {{
  var c = '{character}';
  var el = document.getElementById('{container_id}');
  if (!el) return;
  var xhr = new XMLHttpRequest();
  var url = 'https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0/'
    + encodeURIComponent(c) + '.json';
  xhr.open('GET', url, true);
  xhr.onload = function() {{
    if (xhr.status !== 200) return;
    var d = JSON.parse(xhr.responseText);
    var s = d.strokes;
    var n = s.length;
    var ns = 'http://www.w3.org/2000/svg';
    for (var i = 0; i < n; i++) {{
      var svg = document.createElementNS(ns, 'svg');
      svg.setAttribute('viewBox', '0 0 1024 1024');
      svg.classList.add('stroke-step');
      var g = document.createElementNS(ns, 'g');
      g.setAttribute('transform', 'translate(0,900) scale(1,-1)');
      for (var k = 0; k < n; k++) {{
        var p = document.createElementNS(ns, 'path');
        p.setAttribute('d', s[k]);
        p.setAttribute('fill', k <= i ? '#1A3A5C' : '#D8DAE0');
        g.appendChild(p);
      }}
      svg.appendChild(g);
      el.appendChild(svg);
    }}
  }};
  xhr.send();
}})();
</script>"""
