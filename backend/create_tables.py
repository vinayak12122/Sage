
import asyncio

from database.session import Base, engine
import database.user
import database.chat


async def main():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        print("Tables created successfully!")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
