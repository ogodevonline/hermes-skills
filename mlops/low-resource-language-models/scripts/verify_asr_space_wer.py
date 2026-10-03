#!/usr/bin/env python3
"""Live WER probe for a low-resource ASR model exposed as a Gradio Space.

Pulls N real utterances from a HuggingFace audio dataset (via datasets-server),
POSTs each one to a Gradio Space using the gradio_api HTTP protocol, and
computes micro-WER against the reference transcript. No GPU, no local model.

Usage:
  python3 verify_asr_space_wer.py \
      --space https://atikuwu-whisper-karakalpak-asr.hf.space \
      --api-name transcribe \
      --dataset atikuwu/karakalpak-speech-corpus \
      --split test --n 10 --text-field raw_text [--token $HF_TOKEN] [--params false]

Notes:
  * --params is extra JSON appended after the file in the Space's data array
  * ZeroGPU demos answer `You have exceeded your ZeroGPU runs limit` for
    anonymous callers -- pass --token to authenticate.
"""
import argparse
import base64
import json
import os
import re
import sys
import tempfile
import unicodedata

import requests


def fetch_rows(dataset: str, split: str, n: int, offset: int, audio_field: str):
    r = requests.get(
        "https://datasets-server.huggingface.co/rows",
        params={"dataset": dataset, "config": "default", "split": split,
                "offset": offset, "length": n},
        timeout=120,
    )
    r.raise_for_status()
    payload = r.json()
    if "features" in payload:
        names = [f["name"] for f in payload["features"]]
        if audio_field not in names:
            print(f"! audio field '{audio_field}' not in {names}", file=sys.stderr)
    return payload["rows"]


def norm(text: str):
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip().split()


def word_error_rate(ref: str, hyp: str):
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


def transcribe(space, api_name, path, params, token, result_index):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    with open(path, "rb") as fh:
        up = requests.post(f"{space}/gradio_api/upload", files={"files": fh},
                           headers=headers, timeout=180)
    up.raise_for_status()
    remote = up.json()[0]
    data = [{"path": remote, "meta": {"_type": "gradio.FileData"}}] + list(params)
    ev = requests.post(f"{space}/gradio_api/call/{api_name}", json={"data": data},
                       headers=headers, timeout=180)
    ev.raise_for_status()
    event_id = ev.json()["event_id"]
    with requests.get(f"{space}/gradio_api/call/{api_name}/{event_id}",
                      headers=headers, stream=True, timeout=600) as stream:
        for line in stream.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            payload = json.loads(line[6:])
            if isinstance(payload, dict) and payload.get("error"):
                raise RuntimeError(payload["error"])
            if isinstance(payload, list) and payload:
                return payload[result_index]
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--space", required=True, help="https://<owner>-<space>.hf.space")
    ap.add_argument("--api-name", default="transcribe")
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--text-field", default="text")
    ap.add_argument("--audio-field", default="audio")
    ap.add_argument("--result-index", type=int, default=0)
    ap.add_argument("--params", default="false",
                    help="extra JSON appended after the file (default: false)")
    ap.add_argument("--token", default=os.getenv("HF_TOKEN", ""))
    ap.add_argument("--out", default="asr_wer_results.json")
    args = ap.parse_args()

    params = json.loads(f"[{args.params}]") if args.params else []
    rows = fetch_rows(args.dataset, args.split, args.n, args.offset, args.audio_field)
    tot_err = tot_words = 0
    results = []
    for row in rows:
        idx, rec = row["row_idx"], row["row"]
        ref, aud = rec[args.text_field], rec[args.audio_field]
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp.write(base64.b64decode(aud["bytes"]))
            path = tmp.name
        try:
            hyp = transcribe(args.space, args.api_name, path, params, args.token,
                             args.result_index)
        except Exception as exc:  # quota, timeout, space restart
            print(f"[{idx}] ERROR: {exc}", file=sys.stderr)
            continue
        err, words = word_error_rate(ref, hyp)
        tot_err += err
        tot_words += words
        results.append({"idx": idx, "wer": round(100 * err / max(words, 1), 2),
                        "ref": ref, "hyp": hyp})
        print(f"[{idx}] words={words} err={err} wer={100 * err / max(words, 1):.1f}%")
        print(f"   REF: {ref[:150]}\n   HYP: {hyp[:150]}")

    print("=" * 60)
    print(f"MICRO WER over {len(results)} utts: "
          f"{100 * tot_err / max(tot_words, 1):.2f}% ({tot_err}/{tot_words} words)")
    json.dump(results, open(args.out, "w"), ensure_ascii=False, indent=1)
    print(f"saved -> {args.out}")


if __name__ == "__main__":
    main()
