"""
Compliance Navigator crawler constants.

All categories here must match the frontend WasteCategory values.
"""

from __future__ import annotations


# ============================================================================
# GENERAL WASTE / REGULATORY TERMS
# ============================================================================

GENERAL_WASTE_KEYWORDS = [
    "waste management",
    "waste disposal",
    "waste processing",
    "waste generator",
    "waste handling",
    "waste rules",
    "waste regulation",
    "waste regulations",
    "waste management rules",
    "waste processing facility",
    "waste treatment",
    "waste disposal facility",
    "waste recycling",
    "waste recovery",
    "waste authorization",
    "waste authorisation",
    "waste registration",
]


# ============================================================================
# CATEGORY KEYWORDS
# ============================================================================

CATEGORY_KEYWORDS = {
    "Plastic": [
        "plastic waste",
        "plastic packaging",
        "plastic",
        "single-use plastic",
        "single use plastic",
        "plastic waste management",
        "plastic waste management rules",
        "pwm",
        "pwm rules",
        "extended producer responsibility",
        "epr",
    ],

    "E-Waste": [
        "e-waste",
        "e waste",
        "electronic waste",
        "electrical and electronic equipment",
        "electrical and electronic",
        "e-waste management",
        "e-waste management rules",
        "ewm",
        "ewm rules",
    ],

    "Battery": [
        "battery waste",
        "waste batteries",
        "batteries",
        "battery",
        "battery waste management",
        "battery management rules",
        "battery waste management rules",
        "bwm",
        "bwm rules",
    ],

    "Hazardous": [
        "hazardous waste",
        "hazardous and other wastes",
        "hazardous and other waste",
        "hazardous waste management",
        "hazardous substances",
        "hazardous waste management rules",
        "howm",
        "howm rules",
    ],

    "Solid Waste": [
        "solid waste",
        "municipal solid waste",
        "municipal waste",
        "solid waste management",
        "solid waste management rules",
        "municipal solid waste management",
        "msw",
        "swm",
        "swm rules",
    ],

    "Biomedical": [
        "biomedical waste",
        "bio-medical waste",
        "bio medical waste",
        "biomedical",
        "bio-medical",
        "biomedical waste management",
        "biomedical waste management rules",
        "bmw",
        "bmw rules",
    ],

    "Construction & Demolition": [
        "construction and demolition",
        "construction & demolition",
        "construction demolition",
        "construction waste",
        "demolition waste",
        "c&d waste",
        "c & d waste",
        "c&d rules",
        "construction and demolition waste management",
        "construction and demolition waste management rules",
    ],
}


# ============================================================================
# ALL WASTE RELEVANCE KEYWORDS
# ============================================================================

WASTE_RELEVANCE_KEYWORDS = list(
    dict.fromkeys(
        GENERAL_WASTE_KEYWORDS
        + [
            keyword
            for keywords in CATEGORY_KEYWORDS.values()
            for keyword in keywords
        ]
        + [
            "extended producer responsibility",
            "epr",
            "producer responsibility",
            "recycler",
            "recycling",
            "recyclers",
            "waste treatment",
            "waste disposal",
            "landfill",
            "incineration",
            "incinerator",
            "co-processing",
            "co processing",
            "treatment disposal facility",
            "authorization",
            "authorisation",
            "consent",
            "consent management",
        ]
    )
)


# ============================================================================
# CATEGORY INFERENCE HELPER
# ============================================================================

def infer_categories(text: str) -> list[str]:
    """
    Return all matching frontend-compatible waste categories.
    """

    normalized = (
        text
        .lower()
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
    )

    categories: list[str] = []

    for category, keywords in CATEGORY_KEYWORDS.items():

        for keyword in keywords:

            normalized_keyword = (
                keyword
                .lower()
                .replace("-", " ")
                .replace("_", " ")
                .replace("/", " ")
            )

            if normalized_keyword in normalized:

                categories.append(
                    category
                )

                break

    return list(
        dict.fromkeys(categories)
    )


# ============================================================================
# VALID CATEGORIES
# ============================================================================

VALID_WASTE_CATEGORIES = tuple(
    CATEGORY_KEYWORDS.keys()
)