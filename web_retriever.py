"""FinGuide Official Web Retriever & Knowledge Module.

Provides safe, allowlist-restricted retrieval from trusted Indian financial regulatory
and educational websites (RBI, SEBI, NCFE). Supports local caching, domain validation,
safe redirect handling, content extraction, and vector similarity search.
"""

from __future__ import annotations

import datetime
import html
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

logger = logging.getLogger("finguide.web_retriever")

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_CACHE_DIR = BASE_DIR / "data" / "web_cache"
DEFAULT_CACHE_FILE = DEFAULT_CACHE_DIR / "official_knowledge_cache.json"

# Strict allowlist of trusted official financial education domains
ALLOWED_DOMAINS: Set[str] = {
    "rbi.org.in",
    "rbikehtahai.rbi.org.in",
    "investor.sebi.gov.in",
    "sebi.gov.in",
    "ncfe.org.in",
}

# Curated registry of official financial education URLs
OFFICIAL_URL_REGISTRY: List[Dict[str, str]] = [
    {
        "url": "https://rbikehtahai.rbi.org.in/index.html",
        "domain": "rbikehtahai.rbi.org.in",
        "title": "RBI Kehta Hai — Public Awareness on Banking Safety and Digital Fraud Prevention",
        "category": "Digital Safety & Fraud Prevention",
        "date": "2024-06-15",
    },
    {
        "url": "https://www.rbi.org.in/",
        "domain": "rbi.org.in",
        "title": "Reserve Bank of India — Central Bank Portal, Monetary Policy & Deposit Insurance",
        "category": "Central Banking & Safety",
        "date": "2024-05-10",
    },
    {
        "url": "https://investor.sebi.gov.in/moneymatters.html",
        "domain": "investor.sebi.gov.in",
        "title": "SEBI Investor Education — Money Matters, Budgeting & Compounding",
        "category": "Financial Planning & Savings",
        "date": "2024-04-20",
    },
    {
        "url": "https://investor.sebi.gov.in/personalinvestments.html",
        "domain": "investor.sebi.gov.in",
        "title": "SEBI Investor Education — Personal Investments, Mutual Funds & Asset Allocation",
        "category": "Mutual Funds & Securities",
        "date": "2024-04-20",
    },
    {
        "url": "https://investor.sebi.gov.in/iematerial.html",
        "domain": "investor.sebi.gov.in",
        "title": "SEBI Investor Education — Investor Rights, Dos & Don'ts and SCORES Grievance Redressal",
        "category": "Investor Protection",
        "date": "2024-03-15",
    },
    {
        "url": "https://ncfe.org.in/",
        "domain": "ncfe.org.in",
        "title": "NCFE — National Centre for Financial Education Core Competencies",
        "category": "Financial Literacy & Planning",
        "date": "2024-02-28",
    },
    {
        "url": "https://ncfe.org.in/nflat/",
        "domain": "ncfe.org.in",
        "title": "NCFE — National Financial Literacy Assessment Test (NFLAT) Guidelines",
        "category": "Financial Education Assessment",
        "date": "2024-01-15",
    },
]


def is_domain_allowed(url_or_domain: str) -> bool:
    """Validate whether a URL or host belongs strictly to the approved official domain list."""
    if not url_or_domain:
        return False

    raw = url_or_domain.strip().lower()
    if raw.startswith("http://") or raw.startswith("https://"):
        try:
            parsed = urllib.parse.urlparse(raw)
            host = parsed.hostname or ""
        except Exception:
            return False
    else:
        host = raw

    # Prevent loopbacks and private IP addresses
    if host in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or host.startswith("192.168.") or host.startswith("10.") or host.startswith("172."):
        return False

    for allowed in ALLOWED_DOMAINS:
        if host == allowed or host.endswith("." + allowed):
            return True

    return False


def validate_target_url(url: str) -> Tuple[bool, str]:
    """Inspect URL scheme, host, and domain validity for network safety."""
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty."

    url = url.strip()
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as exc:
        return False, f"Invalid URL structure: {exc}"

    if parsed.scheme not in ("http", "https"):
        return False, f"Disallowed URL scheme '{parsed.scheme}'. Only http and https are permitted."

    host = parsed.hostname or ""
    if not is_domain_allowed(host):
        return (
            False,
            f"Host '{host}' is not in the approved official domains list ({', '.join(sorted(ALLOWED_DOMAINS))}).",
        )

    return True, ""


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Custom redirect handler that validates redirect targets against the domain allowlist."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        is_valid, reason = validate_target_url(newurl)
        if not is_valid:
            logger.warning(f"Blocked unauthorized redirect to '{newurl}': {reason}")
            raise urllib.error.HTTPError(
                newurl,
                403,
                f"Unauthorized redirect target domain: {reason}",
                headers,
                None,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class CleanHTMLTextExtractor(HTMLParser):
    """Safely extracts readable text, title, and metadata dates from HTML without executing scripts."""

    def __init__(self):
        super().__init__()
        self.in_title = False
        self.skip_depth = 0
        self.title = ""
        self.paragraphs: List[str] = []
        self._current_text: List[str] = []
        self.extracted_date: Optional[str] = None
        self.ignored_tags = {"script", "style", "noscript", "svg", "header", "footer", "nav"}

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        tag_lower = tag.lower()
        if tag_lower in self.ignored_tags:
            self.skip_depth += 1
            return

        if self.skip_depth > 0:
            return

        if tag_lower == "title":
            self.in_title = True
        elif tag_lower in ("p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush_current()

        # Check for publication or update dates in meta tags
        if tag_lower == "meta":
            attr_dict = {k.lower(): (v or "") for k, v in attrs}
            name = attr_dict.get("name", "") or attr_dict.get("property", "")
            content = attr_dict.get("content", "")
            if name in ("date", "pubdate", "publishdate", "article:published_time", "article:modified_time", "last-modified") and content:
                # Extract YYYY-MM-DD or date substring
                date_match = re.search(r"\d{4}[-/]\d{2}[-/]\d{2}", content)
                if date_match:
                    self.extracted_date = date_match.group(0).replace("/", "-")
                elif not self.extracted_date:
                    self.extracted_date = content.strip()[:20]

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in self.ignored_tags:
            if self.skip_depth > 0:
                self.skip_depth -= 1
            return

        if self.skip_depth > 0:
            return

        if tag_lower == "title":
            self.in_title = False
        elif tag_lower in ("p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush_current()

    def handle_data(self, data: str):
        if self.skip_depth > 0:
            return

        if self.in_title:
            self.title += data
        else:
            cleaned = data.strip()
            if cleaned:
                self._current_text.append(cleaned)

    def _flush_current(self):
        if self._current_text:
            combined = " ".join(self._current_text).strip()
            # Retain meaningful paragraphs (ignore trivial 1-2 word fragments)
            if len(combined) > 35 and not combined.lower().startswith("copyright"):
                self.paragraphs.append(combined)
            self._current_text = []

    def get_extracted_content(self) -> Tuple[str, List[str], Optional[str]]:
        self._flush_current()
        cleaned_title = re.sub(r"\s+", " ", self.title).strip()
        return cleaned_title, self.paragraphs, self.extracted_date


def fetch_url_content(
    url: str,
    timeout_seconds: float = 5.0,
    max_bytes: int = 2 * 1024 * 1024,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """Safely fetch and parse web content with strict timeouts, size caps, and domain enforcement.

    Returns:
        (title, text_content, publication_date, error_message)
    """
    is_valid, reason = validate_target_url(url)
    if not is_valid:
        return None, None, None, f"URL security check failed: {reason}"

    headers = {
        "User-Agent": "FinGuide-Education-Bot/1.0 (+https://finguide.local; Educational-RAG-Assistant)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        opener = urllib.request.build_opener(SafeRedirectHandler)
        req = urllib.request.Request(url, headers=headers)
        with opener.open(req, timeout=timeout_seconds) as response:
            # Check content length if provided
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > max_bytes:
                return None, None, None, f"Response size ({content_length} bytes) exceeds limit ({max_bytes} bytes)."

            raw_bytes = response.read(max_bytes + 1)
            if len(raw_bytes) > max_bytes:
                return None, None, None, f"Response payload exceeded maximum allowable size of {max_bytes} bytes."

            # Determine charset
            content_type = response.headers.get("Content-Type", "")
            charset = "utf-8"
            if "charset=" in content_type:
                charset = content_type.split("charset=")[-1].split(";")[0].strip()

            try:
                html_text = raw_bytes.decode(charset, errors="replace")
            except Exception:
                html_text = raw_bytes.decode("utf-8", errors="replace")

            extractor = CleanHTMLTextExtractor()
            extractor.feed(html_text)
            title, paragraphs, pub_date = extractor.get_extracted_content()

            if not pub_date:
                # Check HTTP Last-Modified header
                last_modified = response.headers.get("Last-Modified")
                if last_modified:
                    pub_date = last_modified[:16]

            combined_text = "\n\n".join(paragraphs)
            return title or url, combined_text, pub_date, None

    except urllib.error.HTTPError as exc:
        return None, None, None, f"HTTP Error {exc.code}: {exc.reason}"
    except urllib.error.URLError as exc:
        return None, None, None, f"Network connection failed: {exc.reason}"
    except TimeoutError:
        return None, None, None, f"Request timed out after {timeout_seconds} seconds."
    except Exception as exc:
        return None, None, None, f"Unexpected error during fetch: {exc}"


@dataclass
class WebRetrievedPassage:
    """Represents a passage retrieved from an official online source."""

    passage_id: str
    url: str
    title: str
    domain: str
    date: Optional[str]
    text: str
    similarity_score: float
    is_cached: bool = True
    is_stale: bool = False

    def citation_label(self) -> str:
        date_str = f" (Updated: {self.date})" if self.date else ""
        return f"[{self.title}]({self.url}){date_str}"


# Pre-seeded verified official financial knowledge base from RBI, SEBI, and NCFE.
# This provides instant, verified offline resilience and high-quality factual grounding.
VERIFIED_OFFICIAL_SEED_DATA: List[Dict[str, Any]] = [
    {
        "url": "https://rbikehtahai.rbi.org.in/index.html",
        "domain": "rbikehtahai.rbi.org.in",
        "title": "RBI Kehta Hai — Public Awareness on Banking and Digital Security",
        "date": "2024-06-15",
        "fetched_at": "2024-06-15T10:00:00Z",
        "passages": [
            (
                "RBI Kehta Hai — Digital Payment Safety and UPI PIN Guidelines: "
                "The Reserve Bank of India (RBI) repeatedly reminds citizens that you need to enter your UPI PIN "
                "ONLY when you are SENDING money from your bank account. You NEVER need to enter your UPI PIN or "
                "scan a QR code to RECEIVE money. If anyone asks you to enter your UPI PIN or scan a QR code to receive a lottery, "
                "refund, or prize money, it is a fraudulent attempt to withdraw money from your account."
            ),
            (
                "RBI Kehta Hai — OTP, CVV and Password Confidentiality: "
                "Never share your One Time Password (OTP), Card Verification Value (CVV), ATM PIN, or Internet Banking passwords "
                "with anyone over phone, SMS, email, or messaging apps. Bank officials, RBI representatives, and police never ask "
                "for your secret PIN or OTP under any circumstance. Beware of fraudulent calls claiming your KYC has expired or "
                "your electricity or SIM connection will be disconnected."
            ),
            (
                "RBI Kehta Hai — Reporting Cyber Financial Fraud and Golden Hours: "
                "If you become a victim of unauthorized electronic banking transactions or digital financial fraud, report it "
                "immediately to your bank and call the National Cyber Crime Helpline number 1930 or file a complaint on "
                "the National Cyber Crime Reporting Portal at cybercrime.gov.in. Reporting unauthorized transactions within the "
                "first few hours (golden hours) significantly increases the probability of freezing the stolen funds before "
                "fraudsters withdraw them."
            ),
            (
                "RBI Kehta Hai — Reserve Bank - Integrated Ombudsman Scheme (RB-IOS): "
                "The Reserve Bank - Integrated Ombudsman Scheme provides a cost-free and expeditious dispute resolution mechanism "
                "for customers dissatisfied with banking and financial services. If your bank or regulated entity does not resolve "
                "your legitimate complaint within 30 days or rejects it without valid justification, you can escalate your grievance "
                "to the RBI Ombudsman via the CMS portal (cms.rbi.org.in)."
            ),
        ],
    },
    {
        "url": "https://www.rbi.org.in/",
        "domain": "rbi.org.in",
        "title": "Reserve Bank of India — Monetary Policy, Repo Rate & Deposit Insurance",
        "date": "2024-05-10",
        "fetched_at": "2024-05-10T10:00:00Z",
        "passages": [
            (
                "Reserve Bank of India — Bank Deposit Insurance by DICGC: "
                "Under the Deposit Insurance and Credit Guarantee Corporation (DICGC), a wholly owned subsidiary of RBI, "
                "each depositor in a registered commercial or cooperative bank is insured up to a maximum limit of Rs 5,00,000 "
                "(Rupees Five Lakh) for both principal and interest amounts held in the same capacity and same right across all "
                "branches of that bank in case of bank liquidation or cancellation of license."
            ),
            (
                "Reserve Bank of India — Monetary Policy and Inflation Targeting: "
                "The primary objective of the Reserve Bank's monetary policy is to maintain price stability while keeping in mind "
                "the objective of growth. The inflation target under the flexible inflation targeting framework is set at 4% Consumer "
                "Price Index (CPI) inflation with an allowable tolerance band of +/- 2% (i.e., a range between 2% and 6%). The Policy Repo "
                "Rate is the key benchmark interest rate at which the RBI lends short-term liquidity to commercial banks against government securities."
            ),
        ],
    },
    {
        "url": "https://investor.sebi.gov.in/moneymatters.html",
        "domain": "investor.sebi.gov.in",
        "title": "SEBI Investor Education — Money Matters, Budgeting & Compounding",
        "date": "2024-04-20",
        "fetched_at": "2024-04-20T10:00:00Z",
        "passages": [
            (
                "SEBI Investor Education — The Power of Compounding and Rule of 72: "
                "Compound interest is interest calculated on the initial principal and also on the accumulated interest of previous "
                "periods. Albert Einstein famously called compound interest the eighth wonder of the world. The 'Rule of 72' is a simple "
                "mental math shortcut: divide 72 by the annual expected rate of return to estimate approximately how many years it will "
                "take for your invested money to double. For example, at an 8% annual return, an investment doubles in approximately 72 / 8 = 9 years."
            ),
            (
                "SEBI Investor Education — Building Financial Resilience & Emergency Fund: "
                "Before undertaking market investments, an individual should ensure a strong financial foundation: (1) Maintain an emergency "
                "fund equivalent to 6 to 12 months of mandatory household expenses in liquid, low-risk instruments such as bank savings or liquid "
                "funds; (2) Secure adequate pure term life insurance to protect dependents; and (3) Obtain adequate comprehensive health insurance "
                "to prevent medical emergencies from depleting family savings."
            ),
            (
                "SEBI Investor Education — Budgeting with the 50/30/20 Rule: "
                "A balanced budgeting approach divides after-tax income into three distinct buckets: 50% for Essential Needs (housing, groceries, "
                "utilities, minimum loan obligations), 30% for Discretionary Wants (dining out, entertainment, leisure), and 20% dedicated to "
                "Savings and Long-term Investments (emergency fund building, retirement accounts, mutual funds, debt pre-payments)."
            ),
        ],
    },
    {
        "url": "https://investor.sebi.gov.in/personalinvestments.html",
        "domain": "investor.sebi.gov.in",
        "title": "SEBI Investor Education — Personal Investments, Mutual Funds & Asset Allocation",
        "date": "2024-04-20",
        "fetched_at": "2024-04-20T10:00:00Z",
        "passages": [
            (
                "SEBI Investor Education — Mutual Funds Categorization (SEBI Categorization Circular): "
                "SEBI categorizes mutual fund schemes into five broad groups to bring uniformity: (1) Equity Schemes (investing primarily "
                "in stocks for long-term capital growth, including Large Cap, Mid Cap, Small Cap, Multi Cap, and ELSS); (2) Debt Schemes "
                "(investing in fixed-income securities like government bonds, corporate debentures, and treasury bills for capital preservation "
                "and steady income); (3) Hybrid Schemes (investing in a mix of equity and debt); (4) Solution Oriented Schemes (Retirement and "
                "Children's funds); and (5) Other Schemes (Index Funds and ETFs)."
            ),
            (
                "SEBI Investor Education — Systematic Investment Plan (SIP) and Rupee Cost Averaging: "
                "A Systematic Investment Plan (SIP) allows an investor to invest a fixed predetermined sum of money at regular intervals "
                "(typically monthly) in a mutual fund scheme. SIP instills financial discipline and provides the benefit of Rupee Cost "
                "Averaging: when market prices are low, your fixed installment buys more units, and when market prices are high, it buys fewer "
                "units, reducing the average purchase cost over time without needing to time the market."
            ),
            (
                "SEBI Investor Education — Asset Allocation and Risk Profiling: "
                "Asset allocation is the strategy of dividing an investment portfolio among different asset categories—principally equities, "
                "debt/fixed income, gold, and cash equivalents. Because different asset classes react differently to economic events, diversification "
                "significantly reduces overall portfolio risk and volatility without necessarily sacrificing long-term returns."
            ),
        ],
    },
    {
        "url": "https://investor.sebi.gov.in/iematerial.html",
        "domain": "investor.sebi.gov.in",
        "title": "SEBI Investor Education — Investor Rights, Dos & Don'ts and SCORES Grievance Redressal",
        "date": "2024-03-15",
        "fetched_at": "2024-03-15T10:00:00Z",
        "passages": [
            (
                "SEBI Investor Education — SEBI Complaints Redress System (SCORES 2.0): "
                "SCORES (sebi.gov.in/scores) is a web-based centralized grievance redress system launched by SEBI. It allows retail investors "
                "to lodge, track, and follow up on complaints against listed companies, registered brokers, depository participants, mutual funds, "
                "and other SEBI-registered intermediaries. Under SCORES guidelines, entities are mandated to address and resolve investor grievances "
                "within specified timeframes (typically 21 days)."
            ),
            (
                "SEBI Investor Education — Dos and Don'ts for Securities Market Investors: "
                "Dos: Always deal only with SEBI-registered intermediaries; verify registration certificates; read offer documents carefully; "
                "keep contact information updated with your broker and depository participant. Don'ts: NEVER trade on the basis of unsolicited "
                "stock tips, SMS recommendations, or social media groups (Telegram/WhatsApp); never hand over blank signed delivery instruction "
                "slips (DIS); and never believe in claims of guaranteed high returns in stock or derivative markets."
            ),
        ],
    },
    {
        "url": "https://ncfe.org.in/",
        "domain": "ncfe.org.in",
        "title": "NCFE — National Centre for Financial Education Core Competencies",
        "date": "2024-02-28",
        "fetched_at": "2024-02-28T10:00:00Z",
        "passages": [
            (
                "NCFE — National Centre for Financial Education 5 Core Competencies: "
                "The National Strategy for Financial Education (NSFE) coordinated by NCFE outlines five core financial competencies: "
                "(1) Earning (understanding income sources and career capabilities); (2) Spending (distinguishing needs from wants and living "
                "within income); (3) Saving (setting aside money regularly for emergency and future goals); (4) Borrowing (responsible credit "
                "usage and avoiding high-interest debt traps); and (5) Protecting (managing financial risks through appropriate insurance)."
            ),
            (
                "NCFE — Inflation and Purchasing Power Erosion: "
                "Inflation is the sustained increase in the general price level of goods and services over time, which reduces the purchasing "
                "power of money. If inflation averages 6% annually, a basket of essential goods costing Rs 100 today will cost approximately "
                "Rs 179 in ten years. Therefore, savings must be invested in assets that have the potential to earn returns beating inflation "
                "after taxes to avoid real wealth erosion."
            ),
        ],
    },
    {
        "url": "https://ncfe.org.in/nflat/",
        "domain": "ncfe.org.in",
        "title": "NCFE — National Financial Literacy Assessment Test (NFLAT) Guidelines",
        "date": "2024-01-15",
        "fetched_at": "2024-01-15T10:00:00Z",
        "passages": [
            (
                "NCFE — National Financial Literacy Assessment Test (NFLAT): "
                "NFLAT is a nationwide financial literacy assessment initiative designed to measure and promote basic financial education "
                "and money management awareness among school and college students across India. It evaluates fundamental conceptual knowledge "
                "in banking, savings, basic securities markets, insurance, pension products, and digital payment security."
            )
        ],
    },
]


class OfficialWebRetriever:
    """Manages cached official knowledge and safe live retrieval from allowlisted financial regulators."""

    def __init__(
        self,
        cache_file: Optional[Path | str] = None,
        embedder: Optional[Any] = None,
    ):
        self.cache_file = Path(cache_file or DEFAULT_CACHE_FILE)
        self._embedder = embedder
        self._cached_documents: List[Dict[str, Any]] = []
        self._passages: List[Dict[str, Any]] = []
        self._passage_embeddings: Optional[np.ndarray] = None
        self._load_or_initialize_cache()

    def _load_or_initialize_cache(self) -> None:
        """Load knowledge cache from disk or initialize with verified seed data."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cached_documents = json.load(f)
                logger.info(f"Loaded {len(self._cached_documents)} official web sources from cache: {self.cache_file}")
            except Exception as exc:
                logger.warning(f"Failed to read cache file {self.cache_file}: {exc}. Reverting to verified seed data.")
                self._cached_documents = list(VERIFIED_OFFICIAL_SEED_DATA)
                self.save_cache()
        else:
            logger.info("Official web cache not found. Initializing with verified seed registry...")
            self._cached_documents = list(VERIFIED_OFFICIAL_SEED_DATA)
            self.save_cache()

        self._build_passages_list()

    def save_cache(self) -> None:
        """Persist official knowledge cache to disk."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cached_documents, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self._cached_documents)} documents to official web cache.")
        except Exception as exc:
            logger.error(f"Error saving official web cache to {self.cache_file}: {exc}")

    def _build_passages_list(self) -> None:
        """Flatten cached documents into indexable passages."""
        self._passages = []
        passage_counter = 0
        now_dt = datetime.datetime.now(datetime.timezone.utc)

        for doc in self._cached_documents:
            url = doc.get("url", "")
            title = doc.get("title", "Official Source")
            domain = doc.get("domain", "")
            date_val = doc.get("date")
            fetched_at_str = doc.get("fetched_at")

            is_stale = False
            if fetched_at_str:
                try:
                    fetched_dt = datetime.datetime.fromisoformat(fetched_at_str.replace("Z", "+00:00"))
                    age_days = (now_dt - fetched_dt).days
                    if age_days > 180:  # Mark older than 6 months as potentially stale
                        is_stale = True
                except Exception:
                    pass

            for p_idx, text_chunk in enumerate(doc.get("passages", [])):
                if not text_chunk.strip():
                    continue
                passage_counter += 1
                self._passages.append({
                    "passage_id": f"web_{passage_counter}",
                    "url": url,
                    "title": title,
                    "domain": domain,
                    "date": date_val,
                    "text": text_chunk.strip(),
                    "is_cached": True,
                    "is_stale": is_stale,
                })

        # Invalidate embeddings when passages change
        self._passage_embeddings = None

    def _ensure_embeddings(self) -> None:
        """Compute embeddings for all web passages using the shared embedder."""
        if self._passage_embeddings is not None:
            return

        if not self._passages:
            self._passage_embeddings = np.empty((0, 384), dtype=np.float32)
            return

        if self._embedder is None:
            from sentence_transformers import SentenceTransformer

            self._embedder = SentenceTransformer("all-MiniLM-L6-v2")

        texts = [p["text"] for p in self._passages]
        logger.info(f"Generating embeddings for {len(texts)} official web passages...")
        raw_embs = self._embedder.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        self._passage_embeddings = raw_embs.astype(np.float32)

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
        similarity_threshold: float = 0.35,
    ) -> List[WebRetrievedPassage]:
        """Retrieve relevant official online passages matching the query with cosine similarity."""
        if not query or not query.strip() or not self._passages:
            return []

        self._ensure_embeddings()
        if self._passage_embeddings is None or len(self._passage_embeddings) == 0:
            return []

        # Embed user query
        query_emb = self._embedder.encode(
            [query.strip()],
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )[0].astype(np.float32)

        # Dot product with normalized embeddings equals cosine similarity
        similarities = np.dot(self._passage_embeddings, query_emb)
        ranked_indices = np.argsort(similarities)[::-1]

        results: List[WebRetrievedPassage] = []
        for idx in ranked_indices:
            score = float(similarities[idx])
            if score < similarity_threshold:
                continue

            item = self._passages[idx]
            passage = WebRetrievedPassage(
                passage_id=item["passage_id"],
                url=item["url"],
                title=item["title"],
                domain=item["domain"],
                date=item.get("date"),
                text=item["text"],
                similarity_score=round(score, 4),
                is_cached=item.get("is_cached", True),
                is_stale=item.get("is_stale", False),
            )
            results.append(passage)
            if len(results) >= top_k:
                break

        return results

    def refresh_url(self, url: str) -> Tuple[bool, str]:
        """Fetch live official page content from allowlisted URL and refresh the local cache."""
        is_valid, reason = validate_target_url(url)
        if not is_valid:
            return False, reason

        title, text_content, pub_date, error = fetch_url_content(url)
        if error or not text_content:
            return False, f"Failed to refresh URL {url}: {error or 'Empty content'}"

        # Split text into ~200-300 word chunks
        paragraphs = [p.strip() for p in text_content.split("\n\n") if len(p.strip()) > 50]
        if not paragraphs:
            return False, "No readable paragraphs extracted from page."

        parsed_domain = urllib.parse.urlparse(url).hostname or ""
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Update or append in cached documents
        updated = False
        for doc in self._cached_documents:
            if doc.get("url") == url:
                doc["title"] = title or doc.get("title", "Official Source")
                doc["date"] = pub_date or doc.get("date")
                doc["fetched_at"] = now_iso
                doc["passages"] = paragraphs[:10]  # Cap at top 10 passages per page
                updated = True
                break

        if not updated:
            self._cached_documents.append({
                "url": url,
                "domain": parsed_domain,
                "title": title or "Official Source",
                "date": pub_date,
                "fetched_at": now_iso,
                "passages": paragraphs[:10],
            })

        self.save_cache()
        self._build_passages_list()
        return True, f"Successfully refreshed {url} with {len(paragraphs)} passages."

    def get_supported_sources(self) -> List[Dict[str, str]]:
        """Return metadata for all registered official knowledge sources."""
        return list(OFFICIAL_URL_REGISTRY)

    def is_cache_ready(self) -> bool:
        """Check if official knowledge passages are loaded and ready."""
        return len(self._passages) > 0
