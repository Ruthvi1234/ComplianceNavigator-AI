import asyncio
from app.db.mongo import get_db


async def main():
    db = get_db()

    total = await db.documents.count_documents({})

    print("\nTOTAL DOCUMENTS IN MONGODB:", total)

    print("\nWASTE CATEGORY COUNTS:")

    pipeline = [
        {"$unwind": "$waste_category"},
        {
            "$group": {
                "_id": "$waste_category",
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
    ]

    async for row in db.documents.aggregate(pipeline):
        print(row["_id"], ":", row["count"])


asyncio.run(main())