import asyncio

from app.db.mongo import get_client


async def main():
    try:
        result = await get_client().admin.command("ping")
        print("MONGODB CONNECTION OK")
        print(result)
    except Exception as e:
        print("MONGODB CONNECTION FAILED")
        print(type(e).__name__)
        print(str(e))


asyncio.run(main())