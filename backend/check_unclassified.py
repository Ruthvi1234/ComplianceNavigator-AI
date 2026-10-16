import asyncio

from app.db.mongo import get_db


async def main():
    db = get_db()

    print("\nUNCLASSIFIED DOCUMENTS:\n")

    count = 0

    async for doc in db.documents.find(
        {"waste_category": "Unclassified"},
        {
            "title": 1,
            "authority": 1,
            "file_url": 1,
        },
    ):
        count += 1

        print(f"{count}. {doc.get('title', '')}")
        print(f"   Authority: {doc.get('authority', '')}")
        print(f"   PDF: {doc.get('file_url', '')}")
        print()

    print(f"TOTAL UNCLASSIFIED: {count}")


if __name__ == "__main__":
    asyncio.run(main())