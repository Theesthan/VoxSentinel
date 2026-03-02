"""Create all database tables from ORM models."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from tg_common.db.orm_models import Base
from tg_common.config import get_settings

async def main():
    url = get_settings().db_uri
    print(f"Connecting to: {url}")
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("All tables created successfully!")

if __name__ == "__main__":
    asyncio.run(main())
