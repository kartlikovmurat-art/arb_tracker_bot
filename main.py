import asyncio

from app.infrastructure.database import create_tables


async def run():
    await create_tables()
    print("✅ База данных готова")


if __name__ == "__main__":
    asyncio.run(run())