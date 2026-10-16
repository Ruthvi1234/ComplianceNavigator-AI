from __future__ import annotations

import re
import time

from dataclasses import dataclass, field
from typing import Optional

from rank_bm25 import BM25Okapi

from app.models.document import DocumentSearchHit
from app.schemas.search import SearchFilters


# ============================================================
# TOKENIZATION
# ============================================================

_TOKEN_RE = re.compile(
    r"[a-zA-Z0-9]+(?:[-&/][a-zA-Z0-9]+)*"
)


def _tokenize(
    text: str,
) -> list[str]:

    if not text:
        return []

    return [
        token.lower()
        for token in _TOKEN_RE.findall(
            str(text)
        )
    ]

# ============================================================
# BOOLEAN TOKENS
# ============================================================

@dataclass
class BooleanToken:
    type: str
    value: str = ""


# ============================================================
# BOOLEAN TOKENIZER
# ============================================================

def _tokenize_boolean_query(
    query: str,
) -> list[BooleanToken]:
    """
    Tokenize Boolean search syntax.

    Supported:

        plastic
        plastic waste
        plastic AND waste
        plastic OR battery
        plastic NOT battery
        NOT battery
        -battery
        "plastic waste"
        (plastic OR battery) AND hazardous

    Operators are case-insensitive.
    """

    if not query:
        return []

    pattern = re.compile(
        r"""
        (?P<SPACE>\s+)
        |
        (?P<LPAREN>\()
        |
        (?P<RPAREN>\))
        |
        (?P<PHRASE>"[^"]*")
        |
        (?P<MINUS>-[^\s()]+)
        |
        (?P<WORD>[^\s()]+)
        """,
        re.VERBOSE,
    )

    tokens: list[BooleanToken] = []

    for match in pattern.finditer(query):
        kind = match.lastgroup
        value = match.group(0)

        if kind == "SPACE":
            continue

        if kind == "LPAREN":
            tokens.append(
                BooleanToken("LPAREN")
            )
            continue

        if kind == "RPAREN":
            tokens.append(
                BooleanToken("RPAREN")
            )
            continue

        if kind == "PHRASE":
            phrase = value[1:-1].strip()

            if phrase:
                tokens.append(
                    BooleanToken(
                        "PHRASE",
                        phrase.lower(),
                    )
                )

            continue

        if kind == "MINUS":
            term = value[1:].strip()

            if term:
                tokens.append(
                    BooleanToken(
                        "NOT",
                        term.lower(),
                    )
                )

            continue

        if kind == "WORD":
            upper = value.upper()

            if upper == "AND":
                tokens.append(
                    BooleanToken("AND")
                )

            elif upper == "OR":
                tokens.append(
                    BooleanToken("OR")
                )

            elif upper == "NOT":
                tokens.append(
                    BooleanToken("NOT")
                )

            else:
                tokens.append(
                    BooleanToken(
                        "TERM",
                        value.lower(),
                    )
                )

    return tokens


# ============================================================
# BOOLEAN AST
# ============================================================

@dataclass
class BooleanNode:
    type: str

    value: Optional[str] = None

    left: Optional["BooleanNode"] = None

    right: Optional["BooleanNode"] = None


# ============================================================
# BOOLEAN PARSER
# ============================================================

class BooleanParser:
    """
    Boolean grammar:

        expression
            -> OR expression

        OR
            -> AND (OR AND)*

        AND
            -> NOT (AND NOT)*

        NOT
            -> NOT NOT
            -> PRIMARY

        PRIMARY
            -> TERM
            -> PHRASE
            -> '(' expression ')'

    Normal words separated by spaces are treated as AND.

    Example:

        plastic waste

    becomes:

        plastic AND waste
    """

    def __init__(
        self,
        tokens: list[BooleanToken],
    ) -> None:
        self.tokens = tokens
        self.position = 0

    def current(
        self,
    ) -> Optional[BooleanToken]:
        if self.position >= len(self.tokens):
            return None

        return self.tokens[self.position]

    def consume(
        self,
    ) -> Optional[BooleanToken]:
        token = self.current()

        if token is not None:
            self.position += 1

        return token

    def parse(
        self,
    ) -> Optional[BooleanNode]:
        if not self.tokens:
            return None

        node = self.parse_or()

        return node

    # ========================================================
    # OR
    # ========================================================

    def parse_or(
        self,
    ) -> BooleanNode:

        node = self.parse_and()

        while True:
            token = self.current()

            if token is None:
                break

            if token.type != "OR":
                break

            self.consume()

            right = self.parse_and()

            node = BooleanNode(
                type="OR",
                left=node,
                right=right,
            )

        return node

    # ========================================================
    # AND
    # ========================================================

    def parse_and(
        self,
    ) -> BooleanNode:

        node = self.parse_not()

        while True:
            token = self.current()

            if token is None:
                break

            # Explicit AND
            if token.type == "AND":
                self.consume()

                right = self.parse_not()

                node = BooleanNode(
                    type="AND",
                    left=node,
                    right=right,
                )

                continue

            # Implicit AND
            #
            # Example:
            #
            # plastic waste
            #
            # means:
            #
            # plastic AND waste
            #
            if token.type in {
                "TERM",
                "PHRASE",
                "NOT",
                "LPAREN",
            }:
                right = self.parse_not()

                node = BooleanNode(
                    type="AND",
                    left=node,
                    right=right,
                )

                continue

            break

        return node

    # ========================================================
    # NOT
    # ========================================================

    def parse_not(
        self,
    ) -> BooleanNode:

        token = self.current()

        if (
            token is not None
            and token.type == "NOT"
        ):
            self.consume()

            child = self.parse_not()

            return BooleanNode(
                type="NOT",
                left=child,
            )

        return self.parse_primary()

    # ========================================================
    # PRIMARY
    # ========================================================

    def parse_primary(
        self,
    ) -> BooleanNode:

        token = self.current()

        if token is None:
            return BooleanNode(
                type="TERM",
                value="",
            )

        # ----------------------------------------------------
        # Parentheses
        # ----------------------------------------------------

        if token.type == "LPAREN":

            self.consume()

            node = self.parse_or()

            closing = self.current()

            if (
                closing is not None
                and closing.type == "RPAREN"
            ):
                self.consume()

            return node

        # ----------------------------------------------------
        # Phrase
        # ----------------------------------------------------

        if token.type == "PHRASE":

            self.consume()

            return BooleanNode(
                type="PHRASE",
                value=token.value,
            )

        # ----------------------------------------------------
        # Normal term
        # ----------------------------------------------------

        if token.type == "TERM":

            self.consume()

            return BooleanNode(
                type="TERM",
                value=token.value,
            )

        # ----------------------------------------------------
        # Unexpected token
        # ----------------------------------------------------

        self.consume()

        return BooleanNode(
            type="TERM",
            value=token.value,
        )


# ============================================================
# PARSE BOOLEAN EXPRESSION
# ============================================================

def _parse_boolean_expression(
    query: str,
) -> Optional[BooleanNode]:

    tokens = _tokenize_boolean_query(query)

    if not tokens:
        return None

    parser = BooleanParser(tokens)

    return parser.parse()


# ============================================================
# SEARCHABLE DOCUMENT TEXT
# ============================================================

def _document_search_text(
    doc: "IndexedDocument",
) -> str:

    parts = [
        doc.title or "",
        doc.summary or "",
        " ".join(doc.keywords or []),
        " ".join(doc.waste_category or []),
        doc.content_text or "",
    ]

    return " ".join(parts).lower()


# ============================================================
# TERM MATCH
# ============================================================

def _contains_term(
    text: str,
    term: str,
) -> bool:

    term = str(term or "").strip().lower()

    if not term:
        return False

    text_tokens = set(
        _tokenize(text)
    )

    term_tokens = _tokenize(term)

    if not term_tokens:
        return False

    # Single token
    if len(term_tokens) == 1:
        return term_tokens[0] in text_tokens

    # Multi-word term
    #
    # Example:
    #
    # "plastic waste"
    #
    # should require BOTH tokens.
    return all(
        token in text_tokens
        for token in term_tokens
    )


# ============================================================
# PHRASE MATCH
# ============================================================

def _contains_phrase(
    text: str,
    phrase: str,
) -> bool:

    normalized_text = re.sub(
        r"\s+",
        " ",
        str(text or "").lower(),
    ).strip()

    normalized_phrase = re.sub(
        r"\s+",
        " ",
        str(phrase or "").lower(),
    ).strip()

    if not normalized_phrase:
        return False

    return normalized_phrase in normalized_text


# ============================================================
# BOOLEAN EVALUATION
# ============================================================

def _evaluate_boolean(
    node: Optional[BooleanNode],
    text: str,
) -> bool:

    if node is None:
        return True

    # --------------------------------------------------------
    # TERM
    # --------------------------------------------------------

    if node.type == "TERM":

        return _contains_term(
            text,
            node.value or "",
        )

    # --------------------------------------------------------
    # PHRASE
    # --------------------------------------------------------

    if node.type == "PHRASE":

        return _contains_phrase(
            text,
            node.value or "",
        )

    # --------------------------------------------------------
    # NOT
    # --------------------------------------------------------

    if node.type == "NOT":

        return not _evaluate_boolean(
            node.left,
            text,
        )

    # --------------------------------------------------------
    # AND
    # --------------------------------------------------------

    if node.type == "AND":

        return (
            _evaluate_boolean(
                node.left,
                text,
            )
            and
            _evaluate_boolean(
                node.right,
                text,
            )
        )

    # --------------------------------------------------------
    # OR
    # --------------------------------------------------------

    if node.type == "OR":

        return (
            _evaluate_boolean(
                node.left,
                text,
            )
            or
            _evaluate_boolean(
                node.right,
                text,
            )
        )

    return False


# ============================================================
# EXTRACT POSITIVE QUERY TERMS
# ============================================================

def _extract_positive_query_tokens(
    node: Optional[BooleanNode],
) -> list[str]:

    if node is None:
        return []

    # --------------------------------------------------------
    # TERM
    # --------------------------------------------------------

    if node.type == "TERM":

        return _tokenize(
            node.value or ""
        )

    # --------------------------------------------------------
    # PHRASE
    # --------------------------------------------------------

    if node.type == "PHRASE":

        return _tokenize(
            node.value or ""
        )

    # --------------------------------------------------------
    # NOT
    # --------------------------------------------------------

    if node.type == "NOT":

        # Negative terms should NOT be sent to BM25.
        return []

    # --------------------------------------------------------
    # AND
    # --------------------------------------------------------

    if node.type == "AND":

        return (
            _extract_positive_query_tokens(
                node.left
            )
            +
            _extract_positive_query_tokens(
                node.right
            )
        )

    # --------------------------------------------------------
    # OR
    # --------------------------------------------------------

    if node.type == "OR":

        return (
            _extract_positive_query_tokens(
                node.left
            )
            +
            _extract_positive_query_tokens(
                node.right
            )
        )

    return []


# ============================================================
# DOCUMENT MODEL
# ============================================================

@dataclass
class IndexedDocument:

    id: str

    title: str

    authority: str

    document_type: str

    waste_category: list[str]

    state: Optional[str]

    publication_date: str

    reference_code: str

    keywords: list[str]

    summary: str

    source_url: str

    file_url: Optional[str] = None

    page_count: Optional[int] = None

    content_text: str = ""

    tokens: list[str] = field(
        init=False,
        default_factory=list,
    )

    def __post_init__(
        self,
    ) -> None:

        corpus_text = " ".join(
            [
                # Give title more importance
                self.title or "",
                self.title or "",
                self.title or "",

                # Keywords
                " ".join(
                    self.keywords or []
                ),

                " ".join(
                    self.keywords or []
                ),

                # Categories
                " ".join(
                    self.waste_category or []
                ),

                " ".join(
                    self.waste_category or []
                ),

                # Summary
                self.summary or "",

                # Full PDF text
                self.content_text or "",
            ]
        )

        self.tokens = _tokenize(
            corpus_text
        )


# ============================================================
# SEARCH ENGINE
# ============================================================

class HybridSearchEngine:

    def __init__(
        self,
    ) -> None:

        self._docs: list[
            IndexedDocument
        ] = []

        self._bm25: Optional[
            BM25Okapi
        ] = None

    # ========================================================
    # BUILD INDEX
    # ========================================================

    def build(
        self,
        documents: list[
            IndexedDocument
        ],
    ) -> None:

        self._docs = list(
            documents
        )

        if not self._docs:
            self._bm25 = None
            return

        corpus = [
            doc.tokens
            for doc in self._docs
        ]

        self._bm25 = BM25Okapi(
            corpus
        )

    # ========================================================
    # ALL DOCUMENTS
    # ========================================================

    def all_documents(
        self,
    ) -> list[IndexedDocument]:

        return self._docs

    # ========================================================
    # FILTERS
    # ========================================================

    def _matches_filters(
        self,
        doc: IndexedDocument,
        filters: Optional[SearchFilters],
    ) -> bool:

        if not filters:
            return True

        # ----------------------------------------------------
        # AUTHORITY
        # ----------------------------------------------------

        if filters.authority:

            authorities = {
                str(
                    authority.value
                    if hasattr(
                        authority,
                        "value",
                    )
                    else authority
                )
                .strip()
                .upper()
                for authority in filters.authority
            }

            document_authority = (
                str(
                    doc.authority or ""
                )
                .strip()
                .upper()
            )

            if document_authority not in authorities:
                return False

        # ----------------------------------------------------
        # DOCUMENT TYPE
        # ----------------------------------------------------

        if filters.document_type:

            document_types = {
                str(
                    value.value
                    if hasattr(
                        value,
                        "value",
                    )
                    else value
                )
                .strip()
                .upper()
                for value in filters.document_type
            }

            document_type = (
                str(
                    doc.document_type or ""
                )
                .strip()
                .upper()
            )

            if document_type not in document_types:
                return False

        # ----------------------------------------------------
        # WASTE CATEGORY
        # ----------------------------------------------------

        if filters.waste_category:

            wanted = {
                str(
                    value.value
                    if hasattr(
                        value,
                        "value",
                    )
                    else value
                )
                .strip()
                .lower()
                for value in filters.waste_category
            }

            actual = {
                str(value)
                .strip()
                .lower()
                for value in (
                    doc.waste_category
                    or []
                )
            }

            if not wanted.intersection(actual):
                return False

        # ----------------------------------------------------
        # STATE
        # ----------------------------------------------------

        if filters.state:

            requested_state = (
                str(
                    filters.state
                )
                .strip()
                .lower()
            )

            actual_state = (
                str(
                    doc.state or ""
                )
                .strip()
                .lower()
            )

            if requested_state != actual_state:
                return False

        # ----------------------------------------------------
        # DATE FROM
        # ----------------------------------------------------

        if filters.date_from:

            date_from = (
                filters.date_from.isoformat()
            )

            if (
                not doc.publication_date
                or doc.publication_date < date_from
            ):
                return False

        # ----------------------------------------------------
        # DATE TO
        # ----------------------------------------------------

        if filters.date_to:

            date_to = (
                filters.date_to.isoformat()
            )

            if (
                not doc.publication_date
                or doc.publication_date > date_to
            ):
                return False

        return True

    # ========================================================
    # BOOLEAN MATCH
    # ========================================================

    def _boolean_match(
        self,
        doc: IndexedDocument,
        query: str,
    ) -> bool:

        query = str(
            query or ""
        ).strip()

        if not query:
            return True

        searchable_text = (
            _document_search_text(doc)
        )

        expression = (
            _parse_boolean_expression(
                query
            )
        )

        return _evaluate_boolean(
            expression,
            searchable_text,
        )

    # ========================================================
    # QUERY TOKENS
    # ========================================================

    def _query_terms(
        self,
        query: str,
    ) -> list[str]:

        expression = (
            _parse_boolean_expression(
                query
            )
        )

        tokens = (
            _extract_positive_query_tokens(
                expression
            )
        )

        # Remove duplicates while preserving order.
        return list(
            dict.fromkeys(tokens)
        )

    # ========================================================
    # SNIPPET
    # ========================================================

    def _snippet(
        self,
        doc: IndexedDocument,
        query_tokens: set[str],
    ) -> str:

        text = (
            doc.content_text
            or doc.summary
            or doc.title
            or ""
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        if not text:
            return ""

        words = text.split()

        if not words:
            return ""

        # ----------------------------------------------------
        # Find first matching token
        # ----------------------------------------------------

        for index, word in enumerate(words):

            word_tokens = _tokenize(
                word
            )

            if (
                word_tokens
                and any(
                    token in query_tokens
                    for token in word_tokens
                )
            ):

                start = max(
                    0,
                    index - 8,
                )

                end = min(
                    len(words),
                    start + 30,
                )

                result = " ".join(
                    words[start:end]
                )

                if end < len(words):
                    result += "…"

                return result

        # ----------------------------------------------------
        # No matching token
        # ----------------------------------------------------

        result = " ".join(
            words[:30]
        )

        if len(words) > 30:
            result += "…"

        return result

    # ========================================================
    # SEARCH
    # ========================================================

    def search(
        self,
        query: str,
        filters: Optional[SearchFilters] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[
        list[DocumentSearchHit],
        int,
        int,
    ]:

        start = time.perf_counter()

        query = str(
            query or ""
        ).strip()

        # ----------------------------------------------------
        # No documents
        # ----------------------------------------------------

        if not self._docs:

            took_ms = int(
                (
                    time.perf_counter()
                    - start
                )
                * 1000
            )

            return (
                [],
                0,
                took_ms,
            )

        # ----------------------------------------------------
        # Parse Boolean expression
        # ----------------------------------------------------

        expression = (
            _parse_boolean_expression(
                query
            )
            if query
            else None
        )

        # ----------------------------------------------------
        # Positive terms for BM25
        # ----------------------------------------------------

        query_tokens = (
            _extract_positive_query_tokens(
                expression
            )
        )

        # ----------------------------------------------------
        # BM25 ranking
        # ----------------------------------------------------

        if (
            self._bm25 is not None
            and query_tokens
        ):

            scores = (
                self._bm25.get_scores(
                    query_tokens
                )
            )

        else:

            scores = [
                0.0
                for _ in self._docs
            ]

        # ----------------------------------------------------
        # FILTER + BOOLEAN
        # ----------------------------------------------------

        scored: list[
            tuple[
                IndexedDocument,
                float,
            ]
        ] = []

        for doc, score in zip(
            self._docs,
            scores,
        ):

            # ------------------------------------------------
            # UI filters
            # ------------------------------------------------

            if not self._matches_filters(
                doc,
                filters,
            ):
                continue

            # ------------------------------------------------
            # Boolean expression
            # ------------------------------------------------

            if expression is not None:

                if not _evaluate_boolean(
                    expression,
                    _document_search_text(doc),
                ):
                    continue

            scored.append(
                (
                    doc,
                    float(score),
                )
            )

        # ----------------------------------------------------
        # SORT
        # ----------------------------------------------------

        scored.sort(
            key=lambda item: (
                item[1],
                item[0].publication_date or "",
            ),
            reverse=True,
        )

        total = len(
            scored
        )

        # ----------------------------------------------------
        # PAGINATION
        # ----------------------------------------------------

        try:
            page = int(page)
        except (
            TypeError,
            ValueError,
        ):
            page = 1

        try:
            page_size = int(page_size)
        except (
            TypeError,
            ValueError,
        ):
            page_size = 10

        page = max(
            1,
            page,
        )

        page_size = max(
            1,
            page_size,
        )

        offset = (
            page - 1
        ) * page_size

        page_slice = scored[
            offset:
            offset + page_size
        ]

        # ----------------------------------------------------
        # API RESULTS
        # ----------------------------------------------------

        hits: list[
            DocumentSearchHit
        ] = []

        query_token_set = set(
            query_tokens
        )

        for doc, score in page_slice:

            publication_date = (
                doc.publication_date
                or None
            )

            hits.append(
                DocumentSearchHit(
                    id=doc.id,

                    title=doc.title,

                    authority=doc.authority,

                    document_type=doc.document_type,

                    waste_category=(
                        doc.waste_category
                    ),

                    state=doc.state,

                    publication_date=(
                        publication_date
                    ),

                    reference_code=(
                        doc.reference_code
                    ),

                    snippet=self._snippet(
                        doc,
                        query_token_set,
                    ),

                    # Do not return the complete PDF
                    # text in the search response.
                    content_text="",

                    score=round(
                        score,
                        4,
                    ),

                    source_url=(
                        doc.source_url
                    ),

                    file_url=(
                        doc.file_url
                    ),

                    page_count=(
                        doc.page_count
                    ),

                    keywords=(
                        doc.keywords
                    ),
                )
            )

        # ----------------------------------------------------
        # TIMING
        # ----------------------------------------------------

        took_ms = int(
            (
                time.perf_counter()
                - start
            )
            * 1000
        )

        return (
            hits,
            total,
            took_ms,
        )


# ============================================================
# GLOBAL SEARCH ENGINE
# ============================================================

search_engine = HybridSearchEngine()