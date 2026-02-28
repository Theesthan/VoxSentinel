"""Initialize the VoxSentinel database schema and seed sample keyword rules."""
import asyncio
import os
import sys

print("Starting DB initialization...", flush=True)


async def main() -> None:
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from tg_common.db.orm_models import Base, KeywordRuleORM

        url = os.environ.get(
            "TG_DB_URI",
            "postgresql+asyncpg://voxsentinel:changeme@postgres:5432/voxsentinel",
        )
        print(f"Connecting: {url}", flush=True)
        engine = create_async_engine(url)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Tables created.", flush=True)

        # Seed sample keyword rules
        factory = async_sessionmaker(engine, expire_on_commit=False)
        sample_rules = [
            {"keyword": "gun",        "match_type": "exact",  "severity": "critical", "category": "security",   "rule_set_name": "default"},
            {"keyword": "fire",       "match_type": "exact",  "severity": "critical", "category": "security",   "rule_set_name": "default"},
            {"keyword": "help",       "match_type": "exact",  "severity": "high",     "category": "security",   "rule_set_name": "default"},
            {"keyword": "weapon",     "match_type": "fuzzy",  "severity": "critical", "category": "security",   "rule_set_name": "default"},
            {"keyword": "threat",     "match_type": "fuzzy",  "severity": "high",     "category": "security",   "rule_set_name": "default"},
            {"keyword": "complaint",  "match_type": "exact",  "severity": "medium",   "category": "compliance", "rule_set_name": "default"},
            {"keyword": "refund",     "match_type": "exact",  "severity": "low",      "category": "compliance", "rule_set_name": "default"},
        ]

        async with factory() as session:
            for r in sample_rules:
                rule = KeywordRuleORM(
                    rule_set_name=r["rule_set_name"],
                    keyword=r["keyword"],
                    match_type=r["match_type"],
                    severity=r["severity"],
                    category=r["category"],
                    enabled=True,
                )
                session.add(rule)
            await session.commit()
        print(f"Seeded {len(sample_rules)} keyword rules.", flush=True)

        await engine.dispose()
        print("DB initialization complete!", flush=True)

    except Exception as exc:
        print(f"ERROR: {exc}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


asyncio.run(main())
