import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    engine = create_async_engine(os.getenv("DATABASE_URL"))
    async with engine.connect() as conn:
        result = await conn.execute("SELECT id, username, full_name, role FROM users LIMIT 5;")
        for row in result:
            print(row)

if __name__ == "__main__":
    asyncio.run(main())
