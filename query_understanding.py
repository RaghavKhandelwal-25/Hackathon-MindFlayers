"""FinGuide Generalized Query Understanding and Multi-Query Decomposition Module.

Analyzes the structural and semantic information needs of user queries (factual,
comparative, advantages/disadvantages, causal, multi-part, risks/limitations, etc.)
and generates targeted complementary sub-queries to ensure complete facet coverage
during dense semantic retrieval, without requiring additional LLM calls.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class QueryType(str, Enum):
    """Categorizes the primary analytical nature of the user's financial inquiry."""

    FACTUAL = "factual"
    EXPLANATORY = "explanatory"
    CAUSAL = "causal"
    ADVANTAGES_DISADVANTAGES = "advantages_disadvantages"
    COMPARATIVE = "comparative"
    RISKS_LIMITATIONS = "risks_limitations"
    MULTI_PART = "multi_part"
    PRACTICAL_EXAMPLE = "practical_example"
    FOLLOW_UP = "follow_up"


@dataclass
class InformationNeed:
    """Represents the structured interpretation of what information the query demands."""

    original_query: str
    primary_type: QueryType
    detected_aspects: List[str] = field(default_factory=list)
    sub_queries: List[str] = field(default_factory=list)
    requires_multi_query: bool = False
    target_top_k: int = 4


# Regex patterns to detect query structures in a domain-agnostic, generalized manner
ADVANTAGES_DISADVANTAGES_PATTERNS = [
    r"\b(advantages?\s+and\s+disadvantages?)\b",
    r"\b(pros?\s+and\s+cons?)\b",
    r"\b(benefits?\s+and\s+(risks?|limitations?|drawbacks?|disadvantages?))\b",
    r"\b(upsides?\s+and\s+downsides?)\b",
    r"\b(good\s+and\s+bad\s+of)\b",
]

COMPARATIVE_PATTERNS = [
    r"\b(compare|difference\s+between|differ\s+from|versus| vs\.? |as\s+opposed\s+to|better\s+than)\b",
    r"\bhow\s+do\s+(.*?)\s+(differ|compare)\s+from\b",
]

RISKS_LIMITATIONS_PATTERNS = [
    r"\b(risks?\s+and\s+limitations?)\b",
    r"\b(what\s+are\s+(?:the|its|their|all|any)?\s*(?:key\s+)?(risks?|limitations?|pitfalls?|drawbacks?|dangers?))\b",
    r"\b(risks?\s+involved|risks?\s+of)\b",
    r"\b(is\s+it\s+safe\s+to|what\s+can\s+go\s+wrong)\b",
]

CAUSAL_PATTERNS = [
    r"\b(why\s+does|why\s+do|why\s+is|what\s+causes|how\s+does\s+.*?lead\s+to|how\s+does\s+.*?affect|impact\s+of\s+.*?on)\b",
]

PRACTICAL_EXAMPLE_PATTERNS = [
    r"\b(practical\s+example|real-world\s+example|calculate|illustrat(e|ion)|numerical\s+example|with\s+an\s+example)\b",
]


def clean_phrase(phrase: str) -> str:
    """Strip question boilerplates, punctuation, articles, and leading conjunctions."""
    cleaned = re.sub(
        r"(?i)\b(what\s+is|what\s+are|can\s+you|tell\s+me\s+about|explain|please|describe)\b",
        "",
        phrase,
    )
    cleaned = re.sub(r"[^\w\s\-\(\)\/]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Strip leading conjunctions and prepositions
    cleaned = re.sub(r"^(and|or|of|for|with|in|to|the|a|an)\s+", "", cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def extract_comparative_entities(query: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract entity A and entity B from comparative queries (e.g., 'A vs B', 'diff between A and B')."""
    lower = query.lower()

    # Pattern: "difference between X and Y"
    m_between = re.search(r"difference\s+between\s+(.*?)\s+and\s+(.*?)(?:\?|\.|$|in\s+terms\s+of)", lower)
    if m_between:
        e1, e2 = m_between.group(1).strip(), m_between.group(2).strip()
        return clean_phrase(e1), clean_phrase(e2)

    # Pattern: "how do X differ from Y"
    m_differ = re.search(r"how\s+do(?:es)?\s+(.*?)\s+differ\s+from\s+(.*?)(?:\?|\.|$|in\s+terms\s+of)", lower)
    if m_differ:
        e1, e2 = m_differ.group(1).strip(), m_differ.group(2).strip()
        return clean_phrase(e1), clean_phrase(e2)

    # Pattern: "X vs Y" or "X versus Y"
    m_vs = re.search(r"\b(.*?)\s+(?:vs\.?|versus)\s+(.*?)(?:\?|\.|$|in\s+terms\s+of)", lower)
    if m_vs:
        e1, e2 = m_vs.group(1).strip(), m_vs.group(2).strip()
        return clean_phrase(e1), clean_phrase(e2)

    # Pattern: "compare X with Y" / "compare X and Y"
    m_comp = re.search(r"compare\s+(.*?)\s+(?:with|and|to)\s+(.*?)(?:\?|\.|$|in\s+terms\s+of)", lower)
    if m_comp:
        e1, e2 = m_comp.group(1).strip(), m_comp.group(2).strip()
        return clean_phrase(e1), clean_phrase(e2)

    return None, None


def split_multi_part_questions(query: str) -> List[str]:
    """Identify and segment independent sub-questions within a multi-part user query."""
    # Split on question marks
    parts = [p.strip() for p in re.split(r"[?]+", query) if len(p.strip()) > 8]
    if len(parts) > 1:
        return parts

    # Split on distinct clauses joined by ", and what/how/where/who/why"
    clause_splits = re.split(r",\s*(?:and\s+)?(?=(?:what|how|where|why|which|who|can|is|does))\b", query, flags=re.IGNORECASE)
    cleaned_clauses = [c.strip() for c in clause_splits if len(c.strip()) > 10]
    if len(cleaned_clauses) > 1:
        return cleaned_clauses

    return []


def analyze_query_need(query: str) -> InformationNeed:
    """Analyze query structure to deduce information requirements and generate complementary search queries.

    Never hardcodes specific topics; operates on structural linguistics and financial inquiry intent.
    """
    raw_query = query.strip()
    lower_query = raw_query.lower()

    # 1. Check for Multi-part Question (multiple distinct sub-questions)
    multi_parts = split_multi_part_questions(raw_query)
    if len(multi_parts) >= 2:
        sub_queries = [raw_query]
        for part in multi_parts:
            cleaned = clean_phrase(part)
            if cleaned and cleaned not in sub_queries and len(cleaned) > 5:
                sub_queries.append(cleaned)
        return InformationNeed(
            original_query=raw_query,
            primary_type=QueryType.MULTI_PART,
            detected_aspects=["multi_part", "compound_question"],
            sub_queries=sub_queries[:4],
            requires_multi_query=True,
            target_top_k=6,
        )

    # 2. Check for Comparative Query (comparing X vs Y)
    is_comparative = any(re.search(pat, lower_query) for pat in COMPARATIVE_PATTERNS)
    if is_comparative:
        e1, e2 = extract_comparative_entities(raw_query)
        sub_queries = [raw_query]
        aspects = ["comparison", "distinction"]
        if e1 and e2 and len(e1) > 2 and len(e2) > 2:
            sub_queries.append(f"{e1} definition characteristics risks returns")
            sub_queries.append(f"{e2} definition characteristics risks returns")
            sub_queries.append(f"{e1} versus {e2} key differences")
            aspects.extend([e1, e2])
        else:
            # Fallback if entities couldn't be cleanly parsed
            cleaned_core = clean_phrase(raw_query)
            sub_queries.append(f"{cleaned_core} comparison")
            sub_queries.append(f"{cleaned_core} key differences")

        return InformationNeed(
            original_query=raw_query,
            primary_type=QueryType.COMPARATIVE,
            detected_aspects=aspects,
            sub_queries=sub_queries[:4],
            requires_multi_query=True,
            target_top_k=6,
        )

    # 3. Check for Advantages and Disadvantages
    is_adv_dis = any(re.search(pat, lower_query) for pat in ADVANTAGES_DISADVANTAGES_PATTERNS)
    if is_adv_dis:
        cleaned_topic = clean_phrase(
            re.sub(
                r"(?i)\b(advantages?\s+and\s+disadvantages?|pros?\s+and\s+cons?|benefits?\s+and\s+risks?|upsides?\s+and\s+downsides?|of|for|in)\b",
                " ",
                raw_query,
            )
        )
        sub_queries = [
            raw_query,
            f"{cleaned_topic} advantages benefits positive features",
            f"{cleaned_topic} disadvantages risks limitations drawbacks costs",
        ]
        return InformationNeed(
            original_query=raw_query,
            primary_type=QueryType.ADVANTAGES_DISADVANTAGES,
            detected_aspects=["advantages", "disadvantages", "benefits", "risks"],
            sub_queries=sub_queries,
            requires_multi_query=True,
            target_top_k=6,
        )

    # 4. Check for Risks and Limitations
    is_risks = any(re.search(pat, lower_query) for pat in RISKS_LIMITATIONS_PATTERNS)
    if is_risks:
        cleaned_topic = clean_phrase(
            re.sub(r"(?i)\b(risks?\s+and\s+limitations?|what\s+are\s+the\s+risks?|limitations?|drawbacks?|of|in)\b", " ", raw_query)
        )
        sub_queries = [
            raw_query,
            f"{cleaned_topic} risks market risk volatility",
            f"{cleaned_topic} limitations downsides drawbacks",
        ]
        return InformationNeed(
            original_query=raw_query,
            primary_type=QueryType.RISKS_LIMITATIONS,
            detected_aspects=["risks", "limitations"],
            sub_queries=sub_queries,
            requires_multi_query=True,
            target_top_k=5,
        )

    # 5. Check for Causal Query (cause and effect / why / how does X affect Y)
    is_causal = any(re.search(pat, lower_query) for pat in CAUSAL_PATTERNS)
    if is_causal:
        cleaned_core = clean_phrase(raw_query)
        sub_queries = [
            raw_query,
            f"{cleaned_core} mechanism cause effect",
            f"{cleaned_core} impact consequence explanation",
        ]
        return InformationNeed(
            original_query=raw_query,
            primary_type=QueryType.CAUSAL,
            detected_aspects=["cause", "effect", "mechanism"],
            sub_queries=sub_queries,
            requires_multi_query=True,
            target_top_k=5,
        )

    # 6. Check for Practical Example Request
    is_example = any(re.search(pat, lower_query) for pat in PRACTICAL_EXAMPLE_PATTERNS)
    if is_example:
        cleaned_topic = clean_phrase(
            re.sub(r"(?i)\b(practical\s+example|with\s+an\s+example|real-world|illustration|calculate)\b", " ", raw_query)
        )
        sub_queries = [
            raw_query,
            f"{cleaned_topic} concept explanation",
            f"{cleaned_topic} calculation example rule illustration",
        ]
        return InformationNeed(
            original_query=raw_query,
            primary_type=QueryType.PRACTICAL_EXAMPLE,
            detected_aspects=["concept", "example", "calculation"],
            sub_queries=sub_queries,
            requires_multi_query=True,
            target_top_k=5,
        )

    # 7. Default: Direct Factual or Explanatory Query
    return InformationNeed(
        original_query=raw_query,
        primary_type=QueryType.FACTUAL,
        detected_aspects=["direct_explanation"],
        sub_queries=[raw_query],
        requires_multi_query=False,
        target_top_k=4,
    )
