from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class Authority(str, Enum):
    MOEFCC = "MoEFCC"
    CPCB = "CPCB"
    KSPCB = "KSPCB"


class DocumentType(str, Enum):
    RULE = "Rule"
    NOTIFICATION = "Notification"
    CIRCULAR = "Circular"
    GUIDELINE = "Guideline"
    AMENDMENT = "Amendment"


class WasteCategory(str, Enum):
    PLASTIC = "Plastic"
    E_WASTE = "E-Waste"
    BATTERY = "Battery"
    HAZARDOUS = "Hazardous"
    SOLID = "Solid Waste"
    BIOMEDICAL = "Biomedical"
    CONSTRUCTION_DEMOLITION = (
        "Construction & Demolition"
    )
    UNCLASSIFIED = "Unclassified"


class RegulationDocument(BaseModel):

    model_config = ConfigDict(
        use_enum_values=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str

    title: str

    original_title: str | None = None

    authority: Authority

    document_type: DocumentType

    waste_category: list[WasteCategory] = []

    state: str | None = None

    publication_date: date | None = None

    reference_code: str

    keywords: list[str] = []

    summary: str = ""

    source_url: str

    file_url: str | None = None

    page_count: int | None = None

    content_text: str = ""


class DocumentSearchHit(BaseModel):

    model_config = ConfigDict(
        use_enum_values=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str

    title: str

    original_title: str | None = None

    authority: Authority

    document_type: DocumentType

    waste_category: list[WasteCategory] = []

    state: str | None = None

    publication_date: date | None = None

    reference_code: str

    snippet: str = ""

    content_text: str = ""

    score: float = 0.0

    source_url: str

    file_url: str | None = None

    page_count: int | None = None

    keywords: list[str] = []