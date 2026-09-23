#!/usr/bin/env python
"""Transcribe an audio file with faster-whisper and print timestamped segments.

Usage:
    python transcribe_audio.py <audio.wav> [model] [language]

    model    tiny | base | small   (default: base)
    language ISO code, e.g. en, ru (default: auto-detect)

Run with the dedicated venv (NOT the Hermes venv):
    /tmp/whisper_venv/bin/python transcribe_audio.py audio.wav base

Output:
    lang=<code> prob=<0..1>
    [<start>-<end>] <text>
"""
import sys

from faster_whisper import WhisperModel


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    audio = sys.argv[1]
    model_name = sys.argv[2] if len(sys.argv) > 2 else "base"
    language = sys.argv[3] if len(sys.argv) > 3 else None

    model = WhisperModel(model_name, device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio, language=language, vad_filter=True)
    print(f"lang={info.language} prob={info.language_probability:.2f}")
    for s in segments:
        print(f"[{s.start:.1f}-{s.end:.1f}] {s.text.strip()}")


if __name__ == "__main__":
    main()
