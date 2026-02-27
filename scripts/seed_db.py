"""Seed the development database with sample data.

Populates the PostgreSQL database with sample streams, keyword rules,
sessions, transcript segments, and alerts for development and testing.

Usage:
    python scripts/seed_db.py
"""

import asyncio


async def main() -> None:
    """Seed the database with sample development data."""
    ...


if __name__ == "__main__":
    asyncio.run(main())
