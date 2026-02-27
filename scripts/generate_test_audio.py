"""Generate test audio files with known spoken keywords using TTS.

Creates WAV files containing specific spoken keywords and phrases for
deterministic testing of the ASR and NLP pipelines. Uses text-to-speech
synthesis to produce audio with known ground-truth transcriptions.

Usage:
    python scripts/generate_test_audio.py --output data/test_audio/
"""

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for test audio generation."""
    parser = argparse.ArgumentParser(description="Generate test audio with known keywords")
    parser.add_argument("--output", type=str, default="data/test_audio", help="Output directory")
    parser.add_argument("--keywords", nargs="+", default=["bomb", "threat", "emergency"],
                        help="Keywords to embed in audio")
    parser.add_argument("--sample-rate", type=int, default=16000, help="Audio sample rate")
    return parser.parse_args()


def main() -> None:
    """Generate test audio files."""
    ...


if __name__ == "__main__":
    main()
