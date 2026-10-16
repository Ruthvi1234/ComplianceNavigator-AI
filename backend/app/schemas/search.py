from datetime import date

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models.document import (
    Authority,
    DocumentSearchHit,
    DocumentType,
    WasteCategory,
)


class SearchFilters(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    authority: list[Authority] | None = None
    document_type: list[DocumentType] | None = None
    waste_category: list[WasteCategory] | None = None
    state: str | None = None
    date_from: date | None = None
    date_to: date | None = None


class SearchRequest(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    query: str
    filters: SearchFilters | None = None
    page: int = 1
    page_size: int = 20


class SearchResponse(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    query: str
    total: int
    page: int
    page_size: int
    results: list[DocumentSearchHit]
    took_ms: int