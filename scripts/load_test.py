"""Multi-stream load testing tool.

Simulates concurrent RTSP/HLS stream connections to stress-test the
ingestion-to-alert pipeline under high load. Reports throughput,
latency percentiles, and failure rates.

Usage:
    python scripts/load_test.py --streams 50 --duration 300
"""

import argparse
import asyncio


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for load testing."""
    parser = argparse.ArgumentParser(description="Load test VoxSentinel pipeline")
    parser.add_argument("--streams", type=int, default=10, help="Number of concurrent streams")
    parser.add_argument("--duration", type=int, default=60, help="Test duration in seconds")
    parser.add_argument("--api-url", type=str, default="http://localhost:8000", help="API base URL")
    return parser.parse_args()


async def main() -> None:
    """Run multi-stream load test."""
    ...


if __name__ == "__main__":
    asyncio.run(main())
