from __future__ import annotations

from app.services.search.engine import IndexedDocument


VALID_WASTE_CATEGORIES = {
    "Plastic",
    "E-Waste",
    "Battery",
    "Hazardous",
    "Solid Waste",
    "Biomedical",
    "Construction & Demolition",
}


# ============================================================
# CATEGORY CLEANING
# ============================================================

def _clean_categories(value) -> list[str]:
    """
    Normalize waste_category coming from MongoDB.
    """

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        return []

    categories: list[str] = []

    for category in value:
        category = str(category or "").strip()

        if category in VALID_WASTE_CATEGORIES:
            categories.append(category)

    return list(dict.fromkeys(categories))


# ============================================================
# DATE CONVERSION
# ============================================================

def _convert_date(value) -> str:
    """
    Convert Mongo/date values into YYYY-MM-DD where possible.
    """

    if value is None:
        return ""

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()[:10]
        except Exception:
            pass

    value = str(value).strip()

    if not value:
        return ""

    return value[:10]


# ============================================================
# KEYWORD CONVERSION
# ============================================================

def _convert_keywords(value) -> list[str]:
    """
    Normalize keywords into a clean list.
    """

    if isinstance(value, str):
        value = [value]

    if not isinstance(value, list):
        return []

    return [
        str(keyword).strip()
        for keyword in value
        if str(keyword).strip()
    ]


# ============================================================
# CATEGORY INFERENCE
# ============================================================

def _infer_categories_from_text(
    title: str,
    content_text: str,
) -> list[str]:
    """
    Infer waste categories from title + extracted PDF text.

    This is only a fallback when MongoDB does not already
    contain waste_category.
    """

    text = f"{title} {content_text}".lower()

    category_keywords = {
        "Plastic": [
            "plastic waste",
            "plastic packaging",
            "plastic waste management",
            "single use plastic",
            "plastic packaging waste",
            "plastic waste management rules",
        ],

        "E-Waste": [
            "e-waste",
            "e waste",
            "electronic waste",
            "electrical and electronic equipment",
            "e-waste management",
            "e-waste management rules",
        ],

        "Battery": [
            "battery",
            "batteries",
            "battery waste",
            "waste batteries",
            "battery waste management",
            "battery waste management rules",
        ],

        "Hazardous": [
            "hazardous waste",
            "hazardous and other wastes",
            "hazardous and other waste",
            "hazardous waste management",
            "hazardous waste management rules",
        ],

        "Solid Waste": [
            "solid waste",
            "municipal solid waste",
            "solid waste management",
            "solid waste management rules",
            "municipal waste",
        ],

        "Biomedical": [
            "biomedical waste",
            "bio-medical waste",
            "biomedical waste management",
            "biomedical waste management rules",
            "bio medical waste",
        ],

        "Construction & Demolition": [
            "construction and demolition",
            "construction & demolition",
            "construction waste",
            "demolition waste",
            "c&d waste",
            "c & d waste",
            "construction and demolition waste",
        ],
    }

    result: list[str] = []

    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in text:
                result.append(category)
                break

    return list(dict.fromkeys(result))


# ============================================================
# AUTHORITY NORMALIZATION
# ============================================================

def _normalize_authority(value) -> str:
    """
    Normalize authority values.

    Supported canonical values:

        MoEFCC
        CPCB
        KSPCB
    """

    value = str(value or "").strip()

    if not value:
        return ""

    upper = value.upper()

    # --------------------------------------------------------
    # CPCB
    # --------------------------------------------------------

    if (
        "CPCB" in upper
        or "CENTRAL POLLUTION CONTROL BOARD" in upper
    ):
        return "CPCB"

    # --------------------------------------------------------
    # MoEFCC
    # --------------------------------------------------------

    if (
        "MOEFCC" in upper
        or "MOEF&CC" in upper
        or "MOEF & CC" in upper
        or "MINISTRY OF ENVIRONMENT" in upper
    ):
        return "MoEFCC"

    # --------------------------------------------------------
    # KSPCB
    # --------------------------------------------------------

    if (
        "KSPCB" in upper
        or "KARNATAKA STATE POLLUTION CONTROL BOARD" in upper
    ):
        return "KSPCB"

    # Keep unknown authorities instead of dropping documents.
    return value


# ============================================================
# STATE NORMALIZATION
# ============================================================

def _normalize_state(value) -> str | None:
    """
    Normalize state values without destroying None.
    """

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


# ============================================================
# LOAD DOCUMENTS FROM MONGO
# ============================================================

async def load_from_mongo() -> list[IndexedDocument]:
    """
    Load ALL regulation documents from MongoDB.

    IMPORTANT:

    There is intentionally NO year filter here.

    Therefore documents from:
        2016
        2017
        2018
        ...
        2026
        future years

    can all be indexed.

    The MongoDB collection is:

        regulation_documents
    """

    from app.db.mongo import get_db

    db = get_db()

    collection = db["regulation_documents"]

    # ========================================================
    # DEBUG: TOTAL DOCUMENTS IN MONGODB
    # ========================================================

    total_in_mongo = await collection.count_documents({})

    print(
        "\n"
        "==============================================\n"
        "MONGODB DOCUMENT COUNT\n"
        "==============================================\n"
        f"Collection : regulation_documents\n"
        f"Total      : {total_in_mongo}\n"
        "==============================================\n"
    )

    documents: list[IndexedDocument] = []

    # ========================================================
    # LOAD EVERYTHING
    # ========================================================

    cursor = collection.find({})

    async for row in cursor:

        # ----------------------------------------------------
        # ID
        # ----------------------------------------------------

        document_id = str(
            row.get("_id", "")
        )

        if not document_id:
            continue

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        title = str(
            row.get("title", "")
            or ""
        ).strip()

        # IMPORTANT:
        # We do NOT discard the document if title is empty.
        #
        # Older versions had:
        #
        #     if not title:
        #         continue
        #
        # That could silently reduce the index.
        #
        # Instead, create a fallback title.

        if not title:
            title = (
                str(
                    row.get(
                        "original_title",
                        "",
                    )
                    or ""
                ).strip()
                or "Untitled Regulation"
            )

        # ----------------------------------------------------
        # CONTENT
        # ----------------------------------------------------

        content_text = str(
            row.get(
                "content_text",
                "",
            )
            or ""
        )

        # ----------------------------------------------------
        # AUTHORITY
        # ----------------------------------------------------

        authority = _normalize_authority(
            row.get(
                "authority",
                "",
            )
        )

        # ----------------------------------------------------
        # DOCUMENT TYPE
        # ----------------------------------------------------

        document_type = str(
            row.get(
                "document_type",
                "Notification",
            )
            or "Notification"
        ).strip()

        if not document_type:
            document_type = "Notification"

        # ----------------------------------------------------
        # WASTE CATEGORY
        # ----------------------------------------------------

        categories = _clean_categories(
            row.get(
                "waste_category",
                [],
            )
        )

        # ----------------------------------------------------
        # FALLBACK CATEGORY INFERENCE
        # ----------------------------------------------------

        if not categories:
            categories = _infer_categories_from_text(
                title,
                content_text,
            )

        # ----------------------------------------------------
        # STATE
        # ----------------------------------------------------

        state = _normalize_state(
            row.get("state")
        )

        # ----------------------------------------------------
        # PUBLICATION DATE
        # ----------------------------------------------------

        publication_date = _convert_date(
            row.get("publication_date")
        )

        # ----------------------------------------------------
        # REFERENCE CODE
        # ----------------------------------------------------

        reference_code = str(
            row.get(
                "reference_code",
                "",
            )
            or ""
        ).strip()

        # ----------------------------------------------------
        # KEYWORDS
        # ----------------------------------------------------

        keywords = _convert_keywords(
            row.get(
                "keywords",
                [],
            )
        )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        summary = str(
            row.get(
                "summary",
                "",
            )
            or ""
        ).strip()

        # ----------------------------------------------------
        # SOURCE URL
        # ----------------------------------------------------

        source_url = str(
            row.get(
                "source_url",
                "",
            )
            or ""
        ).strip()

        # ----------------------------------------------------
        # FILE URL
        # ----------------------------------------------------

        file_url_value = row.get(
            "file_url"
        )

        file_url = (
            str(file_url_value).strip()
            if file_url_value
            else None
        )

        # ----------------------------------------------------
        # PAGE COUNT
        # ----------------------------------------------------

        page_count = row.get(
            "page_count"
        )

        # ----------------------------------------------------
        # CREATE INDEXED DOCUMENT
        # ----------------------------------------------------

        document = IndexedDocument(
            id=document_id,

            title=title,

            authority=authority,

            document_type=document_type,

            waste_category=categories,

            state=state,

            publication_date=publication_date,

            reference_code=reference_code,

            keywords=keywords,

            summary=summary,

            source_url=source_url,

            file_url=file_url,

            page_count=page_count,

            content_text=content_text,
        )

        documents.append(document)

    # ========================================================
    # FINAL DEBUG INFORMATION
    # ========================================================

    print(
        "\n"
        "==============================================\n"
        "SEARCH INDEX LOAD RESULT\n"
        "==============================================\n"
        f"MongoDB documents : {total_in_mongo}\n"
        f"Indexed documents  : {len(documents)}\n"
        "==============================================\n"
    )

    # Warn if documents disappeared during loading.
    if len(documents) != total_in_mongo:
        print(
            "WARNING: MongoDB contains more documents than "
            "were loaded into the search index."
        )

    return documents