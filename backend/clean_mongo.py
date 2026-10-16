import asyncio

from app.db.mongo import get_db


VALID_CATEGORIES = {
    "Plastic",
    "E-Waste",
    "Battery",
    "Hazardous",
    "Solid Waste",
    "Biomedical",
    "Construction & Demolition",
}


async def clean_database():
    db = get_db()

    cursor = db.documents.find({})

    delete_ids = []

    async for document in cursor:
        categories = document.get("waste_category", [])

        if isinstance(categories, str):
            categories = [categories]

        categories = set(categories)

        if not categories.intersection(VALID_CATEGORIES):
            delete_ids.append(document["_id"])

    print(f"Documents to delete: {len(delete_ids)}")

    if delete_ids:
        result = await db.documents.delete_many(
            {"_id": {"$in": delete_ids}}
        )

        print(f"Deleted: {result.deleted_count}")
    else:
        print("Nothing to delete.")

    remaining = await db.documents.count_documents({})

    print(f"Remaining documents: {remaining}")


if __name__ == "__main__":
    asyncio.run(clean_database())