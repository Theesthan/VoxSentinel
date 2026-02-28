"""Generate test audio files with known spoken keywords using gTTS.

Creates WAV files containing specific spoken keywords and phrases for
deterministic testing of the ASR and NLP pipelines.  Uses Google
Text-to-Speech (gTTS) to synthesize speech, then converts the MP3
output to 16 kHz mono PCM WAV via the standard-library ``audioop``
or ``pydub`` if available.

Usage:
    python scripts/generate_test_audio.py
    python scripts/generate_test_audio.py --output tests/fixtures/test_audio_keywords.wav
"""

from __future__ import annotations

import argparse
import io
import math
import struct
import subprocess
import sys
import wave
from pathlib import Path


_DEFAULT_TEXT = "There is a fire near the entrance and I need help"
_DEFAULT_OUTPUT = "tests/fixtures/test_audio_keywords.wav"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for test audio generation."""
    parser = argparse.ArgumentParser(description="Generate test audio with known keywords")
    parser.add_argument(
        "--output",
        type=str,
        default=_DEFAULT_OUTPUT,
        help="Output WAV path (default: %(default)s)",
    )
    parser.add_argument(
        "--text",
        type=str,
        default=_DEFAULT_TEXT,
        help="Sentence to speak (default: %(default)s)",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16000,
        help="Target WAV sample rate (default: %(default)s)",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        default=False,
        help="Generate synthetic WAV (no gTTS/ffmpeg needed)",
    )
    return parser.parse_args()


def _synthetic_wav_bytes(text: str, sample_rate: int = 16000) -> bytes:
    """Generate a synthetic 16-bit mono PCM WAV with tone bursts.

    Each word in *text* is represented by a short tone burst at a
    unique frequency, separated by silence.  This produces a valid
    WAV file that the ingestion/ASR pipeline can consume without
    needing gTTS or ffmpeg.
    """
    words = text.split()
    samples: list[int] = []
    silence_samples = int(sample_rate * 0.15)  # 150ms silence between words
    word_duration = 0.35  # seconds per word

    for idx, _word in enumerate(words):
        freq = 200 + idx * 50  # unique freq per word
        n_samples = int(sample_rate * word_duration)
        for i in range(n_samples):
            t = i / sample_rate
            # Fade in/out envelope to avoid clicks
            env = 1.0
            fade = int(sample_rate * 0.01)
            if i < fade:
                env = i / fade
            elif i > n_samples - fade:
                env = (n_samples - i) / fade
            val = int(env * 16000 * math.sin(2 * math.pi * freq * t))
            val = max(-32768, min(32767, val))
            samples.append(val)
        samples.extend([0] * silence_samples)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    return buf.getvalue()


def _gtts_to_wav_bytes(text: str, sample_rate: int = 16000) -> bytes:
    """Synthesise *text* with gTTS and return 16-bit mono PCM WAV bytes.

    First attempts conversion via pydub (if installed), falling back
    to ffmpeg on the system PATH, then to synthetic audio.
    """
    try:
        from gtts import gTTS
    except ImportError:
        print("gTTS not available, falling back to synthetic audio", file=sys.stderr)
        return _synthetic_wav_bytes(text, sample_rate)

    try:
        tts = gTTS(text=text, lang="en")
        mp3_buf = io.BytesIO()
        tts.write_to_fp(mp3_buf)
        mp3_buf.seek(0)
    except Exception as exc:
        print(f"gTTS synthesis failed ({exc}), falling back to synthetic audio", file=sys.stderr)
        return _synthetic_wav_bytes(text, sample_rate)

    # ── Try pydub first ──
    try:
        from pydub import AudioSegment

        audio = AudioSegment.from_mp3(mp3_buf)
        audio = audio.set_frame_rate(sample_rate).set_channels(1).set_sample_width(2)
        wav_buf = io.BytesIO()
        audio.export(wav_buf, format="wav")
        return wav_buf.getvalue()
    except Exception:
        pass

    # ── Fallback: ffmpeg subprocess ──
    mp3_buf.seek(0)
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", "pipe:0",
                "-ar", str(sample_rate),
                "-ac", "1",
                "-sample_fmt", "s16",
                "-f", "wav",
                "pipe:1",
            ],
            input=mp3_buf.read(),
            capture_output=True,
            check=True,
        )
        return result.stdout
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # ── Final fallback: synthetic ──
    print("Neither pydub+ffmpeg nor ffmpeg on PATH. Using synthetic WAV.", file=sys.stderr)
    return _synthetic_wav_bytes(text, sample_rate)


def main() -> None:
    """Generate test audio WAV containing keyword-laden speech."""
    args = parse_args()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Generating audio: \"{args.text}\"")
    if args.synthetic:
        wav_data = _synthetic_wav_bytes(args.text, sample_rate=args.sample_rate)
    else:
        wav_data = _gtts_to_wav_bytes(args.text, sample_rate=args.sample_rate)

    output_path.write_bytes(wav_data)
    print(f"Saved {output_path}  ({len(wav_data):,} bytes)")


if __name__ == "__main__":
    main()
