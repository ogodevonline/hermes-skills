#!/usr/bin/env python3
"""PDF -> EPUB converter (no calibre needed).

Usage:
  ~/.venv/bin/python pdf_to_epub.py input.pdf [output.epub] [--title T] [--author A] [--group N]

Requires: pymupdf installed in ~/.venv:
  uv pip install pymupdf --python ~/.venv/bin/python

Verified 04.09.2026 on The_100_Startup.pdf (262 pp text PDF -> 200 KB EPUB,
40 parts). Output renders cleanly in ReadEra; per-word tap-translate works.
Notes:
  - Works only on TEXT pdfs (pymupdf get_text non-empty). Scanned PDFs need OCR first.
  - PDF line-breaks are joined heuristically into paragraphs (sentence-ending
    short lines break paragraphs). Quality is good for prose/non-fiction.
  - No chapter detection: pages are grouped (default 6) into parts. Good enough
    for continuous reading; TOC lists parts.
"""
import sys, os, re, html, zipfile, argparse

def to_html_body(text: str) -> str:
    lines = [ln.rstrip() for ln in text.split('\n')]
    paras, cur = [], []
    for ln in lines:
        if not ln.strip():
            if cur:
                paras.append(' '.join(cur))
                cur = []
            continue
        cur.append(ln.strip())
        if re.search(r'[.!?"\u2019]\s*$', ln) and len(ln) < 90:
            paras.append(' '.join(cur))
            cur = []
    if cur:
        paras.append(' '.join(cur))
    return ''.join(f'<p>{html.escape(p)}</p>' for p in paras)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('epub', nargs='?')
    ap.add_argument('--title', default='')
    ap.add_argument('--author', default='')
    ap.add_argument('--group', type=int, default=6, help='pages per xhtml part')
    a = ap.parse_args()

    import pymupdf
    doc = pymupdf.open(a.pdf)
    pages = [doc[i].get_text().strip() for i in range(doc.page_count)]
    pages = [p for p in pages if p]
    if not pages:
        print('ERROR: no extractable text — scanned PDF? OCR needed.', file=sys.stderr)
        sys.exit(1)
    title = a.title or os.path.splitext(os.path.basename(a.pdf))[0]
    out = a.epub or os.path.splitext(a.pdf)[0] + '.epub'

    build = '/tmp/epub_build'
    os.makedirs(build + '/OEBPS', exist_ok=True)
    os.makedirs(build + '/META-INF', exist_ok=True)
    open(build + '/mimetype', 'w').write('application/epub+zip')
    open(build + '/META-INF/container.xml', 'w').write(
        '<?xml version="1.0"?>\n<container version="1.0" '
        'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
        '<rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>'
        '</rootfiles></container>')

    manifest, spine, ncx = [], [], []
    parts = [pages[i:i + a.group] for i in range(0, len(pages), a.group)]
    for idx, chunk in enumerate(parts, 1):
        fn = f'part-{idx:03d}.xhtml'
        body = '\n'.join(to_html_body(p) for p in chunk)
        open(f'{build}/OEBPS/{fn}', 'w').write(
            f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>'
            f'<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{html.escape(title)}</title></head>'
            f'<body>{body}</body></html>')
        manifest.append(f'<item id="p{idx}" href="{fn}" media-type="application/xhtml+xml"/>')
        spine.append(f'<itemref idref="p{idx}"/>')
        ncx.append(f'<navPoint id="nav{idx}" playOrder="{idx}"><navLabel><text>Part {idx}</text></navLabel><content src="{fn}"/></navPoint>')

    uid = 'urn:uuid:' + re.sub(r'\W+', '', title).lower()[:40]
    open(f'{build}/OEBPS/content.opf', 'w').write(
        f'<?xml version="1.0" encoding="utf-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" '
        f'version="2.0" unique-identifier="uid"><metadata '
        f'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>{html.escape(title)}</dc:title>'
        f'<dc:creator>{html.escape(a.author or "Unknown")}</dc:creator>'
        f'<dc:identifier id="uid">{uid}</dc:identifier><dc:language>en</dc:language></metadata>'
        f'<manifest><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>{"".join(manifest)}</manifest>'
        f'<spine toc="ncx">{"".join(spine)}</spine></package>')
    open(f'{build}/OEBPS/toc.ncx', 'w').write(
        f'<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
        f'<head><meta name="dtb:uid" content="{uid}"/></head><docTitle><text>{html.escape(title)}</text></docTitle>'
        f'<navMap>{"".join(ncx)}</navMap></ncx>')

    if os.path.exists(out):
        os.remove(out)
    zf = zipfile.ZipFile(out, 'w')
    zf.write(build + '/mimetype', 'mimetype', compress_type=zipfile.ZIP_STORED)
    for root, _, files in os.walk(build):
        for fn in files:
            if fn == 'mimetype':
                continue
            full = os.path.join(root, fn)
            zf.write(full, os.path.relpath(full, build), compress_type=zipfile.ZIP_DEFLATED)
    zf.close()
    print(f'OK: {out} ({len(parts)} parts, {len(pages)} pages used)')

if __name__ == '__main__':
    main()
