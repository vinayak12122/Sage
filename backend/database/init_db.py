import asyncio
from database.session import Base,engine
from database.user import User
from database.chat import ChatSession,Message

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(main())