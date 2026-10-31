"""Finbot Query Router and Intent Processing Module.

Handles lightweight intent classification, financial terminology spelling normalization,
and conversational follow-up contextualization without heavy external frameworks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class IntentType(str, Enum):
    GREETING = "greeting"
    THANKS = "thanks"
    PERSONALIZED_ADVICE = "personalized_advice"
    OUT_OF_SCOPE = "out_of_scope"
    FOLLOW_UP = "follow_up"
    FINANCIAL_QUERY = "financial_query"


@dataclass
class RoutingDecision:
    intent: IntentType
    original_query: str
    normalized_query: str
    contextualized_query: str
    direct_response: Optional[str] = None
    should_retrieve: bool = True
    detected_topic: Optional[str] = None


# Common informal abbreviations and typos in financial queries
WORD_REPLACEMENTS: Dict[str, str] = {
    # Chat / text abbreviations
    "wht": "what",
    "wat": "what",
    "wot": "what",
    "r": "are",
    "u": "you",
    "ur": "your",
    "plz": "please",
    "pls": "please",
    "tel": "tell",
    "abt": "about",
    "diff": "difference",
    "diffrence": "difference",
    "differnce": "difference",
    "vs": "versus",
    "expalin": "explain",
    "explian": "explain",
    "defination": "definition",
    "meanig": "meaning",
    # Financial terms spelling correction
    "compund": "compound",
    "compunded": "compounded",
    "intrest": "interest",
    "intrst": "interest",
    "interst": "interest",
    "infltion": "inflation",
    "infaltion": "inflation",
    "mutal": "mutual",
    "mutul": "mutual",
    "muutal": "mutual",
    "fnd": "fund",
    "fnds": "funds",
    "budgt": "budget",
    "budgting": "budgeting",
    "bgeting": "budgeting",
    "bugdet": "budget",
    "traditonal": "traditional",
    "emrgency": "emergency",
    "emergncy": "emergency",
    "emergancy": "emergency",
    "divident": "dividend",
    "dividnt": "dividend",
    "dividends": "dividends",
    "portforlio": "portfolio",
    "portfoio": "portfolio",
    "equty": "equity",
    "equaties": "equities",
    "liabilty": "liability",
    "liabilites": "liabilities",
    "savngs": "savings",
    "saveings": "savings",
    "retirment": "retirement",
    "retirmnt": "retirement",
    "incom": "income",
    "expens": "expense",
    "expences": "expenses",
    "alocation": "allocation",
    "diversifcation": "diversification",
    "volatilty": "volatility",
    "liqudity": "liquidity",
    "amortiztion": "amortization",
    "invst": "invest",
    "investmnt": "investment",
    "investmnts": "investments",
}

# Acronyms to expand when standalone for dense semantic search
ACRONYM_ENRICHMENT: Dict[str, str] = {
    "sip": "SIP (Systematic Investment Plan)",
}

# Greeting keywords & patterns
GREETING_PATTERNS = [
    r"^(hi|hii|hiii|hey|heyy|hello|hellow|howdy|holla|sup|greetings)\b",
    r"^(good\s+(morning|afternoon|evening|day))\b",
    r"^(who\s+are\s+you|what\s+can\s+you\s+do|what\s+is\s+finguide|help\s*me)\b",
]

# Gratitude keywords & patterns
THANKS_PATTERNS = [
    r"^(thanks|thank\s+you|thx|thnx|many\s+thanks|appreciate\s+it|ok\s+thanks|okay\s+thanks|got\s+it\s+thanks)\b",
]

# Personalized financial advice patterns (asking bot to pick stocks, decide allocations, etc.)
PERSONALIZED_ADVICE_PATTERNS = [
    r"\b(should\s+i\s+(buy|sell|invest\s+in))\b",
    r"\b(which\s+(stock|crypto|coin|share|token|equity|mutual\s+fund)\s+should\s+i\s+(buy|invest|pick))\b",
    r"\b(where\s+(should|can)\s+i\s+(put|invest)\s+(my\s+money|money|\d+))\b",
    r"\b(tell\s+me\s+what\s+to\s+buy)\b",
    r"\b(tell\s+me\s+where\s+to\s+invest)\b",
    r"\b(give\s+me\s+.*?(stock|investment|financial)\s+recommendation)\b",
    r"\b(give\s+me\s+(investment|financial)\s+advice)\b",
    r"\b(recommend\s+.*?(stock|crypto|coin|company|fund|shares?))\b",
    r"\b(build\s+(my|a)\s+portfolio\s+for\s+me)\b",
    r"\b(is\s+(tesla|apple|bitcoin|crypto|gold)\s+a\s+good\s+buy\s+right\s+now)\b",
    r"\b(guaranteed\s+returns?)\b",
]

# Obvious non-financial / out-of-scope triggers
OUT_OF_SCOPE_PATTERNS = [
    r"\b(write|create|solve)\s+.*?\b(python|javascript|c\+\+|java|html|css|sql|code|script|program|binary\s+search)\b",
    r"\b(recipe|bake|baking|cooking|cook|pasta|pizza|cake|cookies|bread|soup)\b",
    r"\b(who\s+won|score\s+of|match\s+between|cricket|football|soccer|basketball|ipl|world\s*cup|super\s*bowl)\b",
    r"\b(weather\s+in|weather\s+today|temperature\s+in|forecast\s+for)\b",
    r"\b(tell\s+me\s+a\s+(joke|story|poem))\b",
    r"\b(recommend\s+a\s+(movie|song|film|tv\s+show))\b",
    r"\b(capital\s+of\s+[a-zA-Z]+)\b",
]

# Deictic / follow-up pronouns indicating conversational continuity
FOLLOW_UP_INDICATORS = [
    r"\b(its|it's|their|theirs|them|it|this|that|these|those)\b",
    r"\b(what\s+about|how\s+about|and\s+for|what\s+are\s+(its|the)\s+risks|tell\s+me\s+more)\b",
    r"\b(give\s+(me\s+)?(an\s+)?example)\b",
    r"\b(why\s+should\s+i\s+use\s+it)\b",
    r"\b(how\s+does\s+(that|it)\s+compare)\b",
    r"\b(explain\s+(that|it|this)\s+(again|more|better)?)\b",
    r"\b(explain\s+it\s+like\s+i['’]?m\s+\d+)\b",
]


def normalize_spelling(query: str) -> Tuple[str, bool]:
    """Correct common spelling mistakes, informal abbreviations, and acronyms

    without altering ambiguous financial terms.
    """
    if not query:
        return "", False

    words = re.findall(r"\b[\w\(\)\-\.]+\b|[^\w\s]", query, flags=re.UNICODE)
    modified = False
    normalized_tokens: List[str] = []

    for token in words:
        lower_token = token.lower()
        if lower_token in WORD_REPLACEMENTS:
            normalized_tokens.append(WORD_REPLACEMENTS[lower_token])
            modified = True
        elif lower_token in ACRONYM_ENRICHMENT:
            # Enrich acronym for improved embedding retrieval
            normalized_tokens.append(ACRONYM_ENRICHMENT[lower_token])
            modified = True
        else:
            normalized_tokens.append(token)

    # Reconstruct text with natural spacing
    normalized_query = " ".join(normalized_tokens)
    # Fix punctuation spacing (e.g., "what is it ?" -> "what is it?")
    normalized_query = re.sub(r"\s+([?.!,;:])", r"\1", normalized_query)

    return normalized_query.strip(), modified


def extract_topic_from_text(text: str) -> Optional[str]:
    """Extract primary financial subject or topic from a query or response."""
    if not text:
        return None

    # Remove generic question templates
    cleaned = re.sub(
        r"(?i)\b(what\s+is|what\s+are|explain|how\s+does|how\s+do|tell\s+me\s+about|can\s+you|please|a|an|the|meaning\s+of|definition\s+of)\b",
        "",
        text,
    )
    cleaned = re.sub(r"[^\w\s]", "", cleaned).strip()
    words = cleaned.split()

    if words:
        # Keep up to the first 4 words of the subject
        return " ".join(words[:4]).strip()
    return None


def resolve_follow_up_context(
    query: str, history: Optional[List[Dict[str, Any]]]
) -> Tuple[str, Optional[str]]:
    """Enrich a follow-up query with the active conversational topic from previous

    turns.
    """
    if not history:
        return query, None

    # Find the most recent user turn that had substantial topic content
    for item in reversed(history):
        if item.get("role") == "user":
            prev_content = item.get("content", "")
            topic = extract_topic_from_text(prev_content)
            if topic:
                contextualized = f"{topic}: {query}"
                return contextualized, topic

    return query, None


def classify_intent(
    query: str, history: Optional[List[Dict[str, Any]]] = None
) -> RoutingDecision:
    """Classify the user query intent and prepare appropriate response or retrieval query."""
    raw_query = query.strip()
    lower_query = raw_query.lower()

    # Empty query handling
    if not raw_query:
        return RoutingDecision(
            intent=IntentType.FINANCIAL_QUERY,
            original_query=raw_query,
            normalized_query="",
            contextualized_query="",
            direct_response="Please enter a financial question or topic you would like to explore.",
            should_retrieve=False,
        )

    # 1. Check for Greeting
    for pattern in GREETING_PATTERNS:
        if re.search(pattern, lower_query):
            greeting_msg = (
                "👋 **Hello! Welcome to Finbot.**\n\n"
                "I am your AI assistant for financial education. I can help answer questions on:\n"
                "- **Personal Finance & Budgeting** (the 50/30/20 rule, emergency funds, debt snowball vs. avalanche)\n"
                "- **Investing Fundamentals** (stocks, bonds, index funds, expense ratios, compound interest)\n"
                "- **Retirement Planning** (401k employer matches, Traditional IRA vs. Roth IRA)\n\n"
                "All answers are grounded in verified financial documents with citations. What financial topic would you like to explore today?"
            )
            return RoutingDecision(
                intent=IntentType.GREETING,
                original_query=raw_query,
                normalized_query=raw_query,
                contextualized_query=raw_query,
                direct_response=greeting_msg,
                should_retrieve=False,
            )

    # 2. Check for Gratitude / Thanks
    for pattern in THANKS_PATTERNS:
        if re.search(pattern, lower_query):
            thanks_msg = (
                "You are very welcome! 😊\n\n"
                "Feel free to ask whenever you have more questions about managing, budgeting, or investing your money."
            )
            return RoutingDecision(
                intent=IntentType.THANKS,
                original_query=raw_query,
                normalized_query=raw_query,
                contextualized_query=raw_query,
                direct_response=thanks_msg,
                should_retrieve=False,
            )

    # 3. Check for Personalized Investment Advice Request
    for pattern in PERSONALIZED_ADVICE_PATTERNS:
        if re.search(pattern, lower_query):
            advice_msg = (
                "⚠️ **Educational Guidance Only**: I cannot provide personalized investment advice, stock picks, or portfolio recommendations.\n\n"
                "Choosing specific investments depends on your unique financial situation, income stability, tax bracket, and risk tolerance, which should be evaluated with a certified financial planner.\n\n"
                "**Educational Principles to Consider:**\n"
                "1. **Emergency Reserve**: Financial experts recommend building a 3 to 6-month liquid emergency fund in a High-Yield Savings Account before taking market risk.\n"
                "2. **Broad Diversification**: Investing through low-cost index funds or ETFs exposes you to broad markets rather than the unsystematic risk of single companies.\n"
                "3. **Time Horizon**: Higher-volatility assets (like equities) are historically suited for horizons of 5+ years, while short-term capital is safer in fixed income or cash equivalents.\n\n"
                "Would you like to explore how broad index funds, asset classes, or risk management principles work?"
            )
            return RoutingDecision(
                intent=IntentType.PERSONALIZED_ADVICE,
                original_query=raw_query,
                normalized_query=raw_query,
                contextualized_query=raw_query,
                direct_response=advice_msg,
                should_retrieve=False,
            )

    # 4. Check for Out-of-Scope queries
    for pattern in OUT_OF_SCOPE_PATTERNS:
        if re.search(pattern, lower_query):
            scope_msg = (
                "ℹ️ **Topic Outside Scope**: Finbot is dedicated exclusively to **financial education and investing literacy**.\n\n"
                "I cannot answer questions related to software coding, cooking recipes, weather, pop culture, or general knowledge. "
                "Please feel free to ask questions about budgeting, mutual funds, compound interest, retirement accounts, or financial planning!"
            )
            return RoutingDecision(
                intent=IntentType.OUT_OF_SCOPE,
                original_query=raw_query,
                normalized_query=raw_query,
                contextualized_query=raw_query,
                direct_response=scope_msg,
                should_retrieve=False,
            )

    # Normalize spelling and abbreviations for retrieval
    normalized_q, _ = normalize_spelling(raw_query)

    # 5. Check for Follow-up Context
    is_follow_up = False
    detected_topic = None
    if history and len(history) > 0:
        for indicator in FOLLOW_UP_INDICATORS:
            if re.search(indicator, lower_query):
                is_follow_up = True
                break

    if is_follow_up:
        contextualized_q, detected_topic = resolve_follow_up_context(
            normalized_q, history
        )
        return RoutingDecision(
            intent=IntentType.FOLLOW_UP,
            original_query=raw_query,
            normalized_query=normalized_q,
            contextualized_query=contextualized_q,
            direct_response=None,
            should_retrieve=True,
            detected_topic=detected_topic,
        )

    # 6. Default: Genuine Financial Education Query
    return RoutingDecision(
        intent=IntentType.FINANCIAL_QUERY,
        original_query=raw_query,
        normalized_query=normalized_q,
        contextualized_query=normalized_q,
        direct_response=None,
        should_retrieve=True,
    )
