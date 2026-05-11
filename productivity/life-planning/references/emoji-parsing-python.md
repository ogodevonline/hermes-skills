# Emoji parsing in Python re

Python's `re` module does NOT support `\X` (grapheme cluster / extended unicode sequence).
PCRE does, but Python re does not. Use `regex` third-party module if you need \X.

## The problem

Complex emoji like `👨‍👩‍👧` (family: man + ZWJ + woman + ZWJ + girl) consist of
multiple Unicode code points. A single-character approach like `r'[💼❤️👨‍👩‍👧]'`
fails because:
- `👨‍👩‍👧` is actually 5+ codepoints
- `❤️` includes a variation selector U+FE0F
- Python `re` character classes match individual codepoints, not grapheme clusters

## The fix (used in planning.py)

Instead of regex matching on emoji, split the line by `|` and check `startswith`:

```python
for line in text.splitlines():
    cols = [c.strip() for c in line.split('|')]
    if len(cols) < 5:
        continue
    emoji_name = cols[1]  # e.g. "👨‍👩‍👧 Семья"
    for sname, (semoji, _) in SPHERE_MAP.items():
        if emoji_name.startswith(semoji):
            # found it
```

This is more robust than any regex approach for emoji-containing tables.

## Alternative: use `regex` module

```python
import regex  # pip install regex
# now \X works
matches = regex.findall(r'\|\s*(\X)\s*(\S+?)\s*\|\s*(\d+)\s*\|', text)
```

But adds a dependency. The line-split approach is zero-dependency.
