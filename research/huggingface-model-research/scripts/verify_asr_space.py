#!/usr/bin/env python3
"""Live-check an ASR Gradio Space on real dataset samples + micro-WER.

Usage:
  python3 verify_asr_space.py --space https://<space>.hf.space \
      --dataset atikuwu/karakalpak-speech-corpus --split test --n 5 \
      --ref-field raw_text --api transcribe

Requires: requests.  Anonymous ZeroGPU spaces allow only ~2-3 runs before
'You have exceeded your ZeroGPU runs limit' -- pass --token or use your own GPU.
"""
import argparse
import base64
import json
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

import requests


def get_rows(dataset, config, split, n, offset=0):
    r = requests.get(
        "https://datasets-server.huggingface.co/rows",
        params={"dataset": dataset, "config": config, "split": split,
                "offset": offset, "length": n},
        timeout=90,
    )
    r.raise_for_status()
    return r.json()["rows"]


def norm(text):
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip().split()


def wer(ref, hyp):
    r, h = norm(ref), norm(hyp)
    d = [[0] * (len(h) + 1) for _ in range(len(r) + 1)]
    for i in range(len(r) + 1):
        d[i][0] = i
    for j in range(len(h) + 1):
        d[0][j] = j
    for i in range(1, len(r) + 1):
        for j in range(1, len(h) + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (r[i - 1] != h[j - 1]))
    return d[len(r)][len(h)], len(r)


def transcribe(space, api, path, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with open(path, "rb") as fh:
        up = requests.post(f"{space}/gradio_api/upload", files={"files": fh},
                           headers=headers, timeout=120)
    up.raise_for_status()
    spath = up.json()[0]
    ev = requests.post(
        f"{space}/gradio_api/call/{api}",
        json={"data": [{"path": spath, "meta": {"_type": "gradio.FileData"}}, False]},
        headers=headers, timeout=120,
    )
    ev.raise_for_status()
    eid = ev.json()["event_id"]
    with requests.get(f"{space}/gradio_api/call/{api}/{eid}", headers=headers,
                      stream=True, timeout=300) as s:
        for line in s.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("event: error"):
                raise RuntimeError("space error (ZeroGPU quota? auth?)")
            if line.startswith("data: "):
                payload = json.loads(line[6:])
                return payload[0] if isinstance(payload, list) else payload
    raise RuntimeError("no result in SSE stream")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--space", required=True, help="https://<name>.hf.space")
    p.add_argument("--dataset", required=True)
    p.add_argument("--config", default="default")
    p.add_argument("--split", default="test")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--ref-field", default="raw_text")
    p.add_argument("--api", default="transcribe", help="gradio api_name")
    p.add_argument("--token", default=None, help="HF token (raises ZeroGPU quota)")
    a = p.parse_args()

    rows = get_rows(a.dataset, a.config, a.split, a.n)
    tot_err = tot_words = done = 0
    for row in rows:
        body = row["row"]
        ref = body.get(a.ref_field) or body.get("text") or ""
        tmp = Path(tempfile.gettempdir()) / f"sample_{row['row_idx']}.ogg"
        tmp.write_bytes(base64.b64decode(body["audio"]["bytes"]))
        try:
            hyp = transcribe(a.space, a.api, str(tmp), a.token)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"[{row['row_idx']}] ERROR {exc}", file=sys.stderr)
            continue
        err, words = wer(ref, hyp)
        tot_err += err
        tot_words += words
        done += 1
        print(f"[{row['row_idx']}] words={words} err={err} wer={100 * err / max(words, 1):.1f}%")
        print(f"   REF: {ref[:150]}")
        print(f"   HYP: {hyp[:150]}")
    if done:
        print("=" * 60)
        print(f"MICRO WER over {done} utts: {100 * tot_err / max(tot_words, 1):.2f}%")


if __name__ == "__main__":
    main()
