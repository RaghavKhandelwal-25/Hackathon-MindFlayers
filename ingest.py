"""FinGuide Document Ingestion Pipeline.

Extracts text page-by-page from PDF files in data/pdfs/ using PyMuPDF,
chunks the text with preserved document and page metadata, computes
dense vector embeddings using sentence-transformers/all-MiniLM-L6-v2,
and persists a FAISS CPU index with corresponding metadata.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Tuple

try:
    import pymupdf as fitz
except ImportError:
    import fitz
import dotenv
import numpy as np

# Load environment variables explicitly from finguide/.env if present
_BASE_DIR = Path(__file__).resolve().parent
_ENV_PATH = _BASE_DIR / ".env"
if _ENV_PATH.exists():
    dotenv.load_dotenv(dotenv_path=_ENV_PATH, override=True)
else:
    dotenv.load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("finguide.ingest")

DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_CHUNK_SIZE = 500  # characters per chunk
DEFAULT_CHUNK_OVERLAP = 100  # character overlap between chunks


@dataclass
class DocumentChunk:
    chunk_id: int
    doc_name: str
    doc_title: str
    page_number: int
    chunk_index_in_page: int
    text: str
    char_count: int


def get_default_paths() -> Tuple[Path, Path]:
    """Resolve base data and vectorstore directories relative to this file."""
    base_dir = Path(__file__).resolve().parent
    data_dir = base_dir / "data" / "pdfs"
    vectorstore_dir = base_dir / "vectorstore"
    return data_dir, vectorstore_dir


def split_text_into_chunks(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """Split text into overlapping chunks, respecting paragraph or sentence boundaries
    when possible while strictly preventing stalled advancement.
    """
    if not text:
        return []

    text = text.strip()
    if len(text) <= chunk_size:
        return [text]

    chunks: List[str] = []
    start = 0
    text_length = len(text)
    min_advance = max(1, chunk_size - chunk_overlap)

    while start < text_length:
        end = min(start + chunk_size, text_length)

        if end >= text_length:
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # Search for a clean break point between (start + min_advance) and end
        search_start = start + (min_advance // 2)
        split_point = -1

        # Check for paragraph break
        newline_pos = text.rfind("\n\n", search_start, end)
        if newline_pos != -1:
            split_point = newline_pos + 2
        else:
            # Check for sentence end (.!?) followed by space or newline
            for punct in [". ", "? ", "! ", ".\n"]:
                pos = text.rfind(punct, search_start, end)
                if pos != -1:
                    split_point = max(split_point, pos + len(punct))

            if split_point == -1:
                # Fallback to word boundary
                space_pos = text.rfind(" ", search_start, end)
                if space_pos != -1:
                    split_point = space_pos + 1
                else:
                    split_point = end

        chunk = text[start:split_point].strip()
        if chunk:
            chunks.append(chunk)

        # Move to next start, guaranteeing at least min_advance progress
        next_start = split_point - chunk_overlap
        start = max(start + (min_advance // 2), next_start)

    return chunks


def extract_chunks_from_pdf(
    pdf_path: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    start_chunk_id: int = 0,
) -> Tuple[List[DocumentChunk], int]:
    """Extract text page-by-page from a single PDF using PyMuPDF, skipping empty pages

    and generating DocumentChunk objects with document name and page numbers.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    chunks: List[DocumentChunk] = []
    current_chunk_id = start_chunk_id

    try:
        doc = fitz.open(pdf_path)
    except Exception as exc:
        logger.error(f"Failed to open PDF document '{pdf_path.name}': {exc}")
        raise RuntimeError(f"Could not read PDF '{pdf_path.name}': {exc}") from exc

    try:
        # Determine human-friendly document title
        raw_title = doc.metadata.get("title", "") if doc.metadata else ""
        if raw_title and raw_title.strip():
            doc_title = raw_title.strip()
        else:
            doc_title = pdf_path.stem.replace("_", " ").replace("-", " ").title()

        total_pages = len(doc)
        logger.info(f"Processing '{pdf_path.name}' ({total_pages} pages, title: '{doc_title}')...")

        for page_idx in range(total_pages):
            page_number = page_idx + 1  # 1-indexed for human readability
            try:
                page = doc.load_page(page_idx)
                page_text = page.get_text("text").strip()
            except Exception as page_exc:
                logger.warning(
                    f"Warning: Extraction failed on page {page_number} of '{pdf_path.name}': {page_exc}"
                )
                continue

            # Skip empty or trivially blank pages
            if not page_text or len(page_text) < 15:
                logger.debug(f"Skipping empty or near-empty page {page_number} in '{pdf_path.name}'")
                continue

            page_chunks = split_text_into_chunks(
                page_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
            )

            for chunk_idx, chunk_text in enumerate(page_chunks):
                chunk = DocumentChunk(
                    chunk_id=current_chunk_id,
                    doc_name=pdf_path.name,
                    doc_title=doc_title,
                    page_number=page_number,
                    chunk_index_in_page=chunk_idx,
                    text=chunk_text,
                    char_count=len(chunk_text),
                )
                chunks.append(chunk)
                current_chunk_id += 1

    finally:
        doc.close()

    logger.info(
        f"Extracted {len(chunks)} chunks from '{pdf_path.name}' across {total_pages} pages."
    )
    return chunks, current_chunk_id


def ingest_documents(
    data_dir: Path | str | None = None,
    vectorstore_dir: Path | str | None = None,
    model_name: str = DEFAULT_MODEL_NAME,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> int:
    """Ingest all PDFs in data_dir, compute embeddings locally with SentenceTransformers,

    and persist FAISS index & metadata to vectorstore_dir.

    Returns the number of indexed chunks.
    """
    default_data, default_vs = get_default_paths()
    data_path = Path(data_dir) if data_dir else default_data
    vs_path = Path(vectorstore_dir) if vectorstore_dir else default_vs

    if not data_path.exists() or not data_path.is_dir():
        raise FileNotFoundError(
            f"PDF source directory does not exist: '{data_path.resolve()}'. "
            "Please create the directory and place financial PDF documents inside."
        )

    seen_paths = set()
    pdf_files = []
    for pattern in ["*.pdf", "*.PDF"]:
        for p in data_path.glob(pattern):
            resolved = p.resolve()
            if resolved not in seen_paths and resolved.is_file():
                seen_paths.add(resolved)
                pdf_files.append(p)
    pdf_files.sort(key=lambda x: x.name.lower())

    if not pdf_files:
        raise ValueError(
            f"No PDF documents found in '{data_path.resolve()}'. "
            "Please add at least one supported .pdf file to data/pdfs/ before running ingestion."
        )

    logger.info(f"Found {len(pdf_files)} PDF file(s) in '{data_path.resolve()}'.")

    all_chunks: List[DocumentChunk] = []
    current_chunk_id = 0
    extraction_errors: List[str] = []

    for pdf_file in pdf_files:
        try:
            chunks, current_chunk_id = extract_chunks_from_pdf(
                pdf_path=pdf_file,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                start_chunk_id=current_chunk_id,
            )
            all_chunks.extend(chunks)
        except Exception as exc:
            error_msg = f"Failed extracting from {pdf_file.name}: {exc}"
            logger.error(error_msg)
            extraction_errors.append(error_msg)

    if not all_chunks:
        detail = f" Errors encountered: {extraction_errors}" if extraction_errors else ""
        raise ValueError(
            f"No valid text chunks could be extracted from {len(pdf_files)} PDF(s).{detail}"
        )

    logger.info(f"Total extracted chunks across all documents: {len(all_chunks)}.")

    # Generate embeddings locally using SentenceTransformers
    logger.info(f"Loading local embedding model: '{model_name}'...")
    try:
        from sentence_transformers import SentenceTransformer
        import faiss
    except ImportError as e:
        raise ImportError(
            f"Required library missing ({e.name}). Ensure sentence-transformers and faiss-cpu are installed."
        ) from e

    embedder = SentenceTransformer(model_name)
    texts_to_embed = [chunk.text for chunk in all_chunks]

    logger.info(f"Generating embeddings for {len(texts_to_embed)} chunks...")
    embeddings = embedder.encode(
        texts_to_embed,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )

    embeddings = np.array(embeddings, dtype=np.float32)
    # Normalize for cosine similarity via IndexFlatIP
    faiss.normalize_L2(embeddings)

    dimension = embeddings.shape[1]
    logger.info(f"Creating FAISS IndexFlatIP with dimension {dimension}...")
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings)

    # Persist index and metadata
    vs_path.mkdir(parents=True, exist_ok=True)
    index_file = vs_path / "index.faiss"
    metadata_file = vs_path / "metadata.json"

    logger.info(f"Writing FAISS index to '{index_file.resolve()}'...")
    faiss.write_index(index, str(index_file))

    metadata_records = [asdict(chunk) for chunk in all_chunks]
    logger.info(f"Writing metadata ({len(metadata_records)} records) to '{metadata_file.resolve()}'...")
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata_records, f, indent=2, ensure_ascii=False)

    logger.info("Ingestion completed successfully!")
    logger.info(f"Total documents: {len(pdf_files)}")
    logger.info(f"Total chunks indexed: {len(all_chunks)}")
    logger.info(f"Vector dimension: {dimension}")
    if extraction_errors:
        logger.warning(f"Note: {len(extraction_errors)} documents had extraction warnings.")

    return len(all_chunks)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="FinGuide PDF Ingestion and Vector Store Generation"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Path to directory containing PDF files (defaults to finguide/data/pdfs)",
    )
    parser.add_argument(
        "--vectorstore-dir",
        type=str,
        default=None,
        help="Path to directory where FAISS index and metadata will be saved (defaults to finguide/vectorstore)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help="Maximum character length per chunk (default: 500)",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help="Character overlap between consecutive chunks (default: 100)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL_NAME,
        help="HuggingFace model name for embeddings (default: all-MiniLM-L6-v2)",
    )

    args = parser.parse_args()

    try:
        count = ingest_documents(
            data_dir=args.data_dir,
            vectorstore_dir=args.vectorstore_dir,
            model_name=args.model,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
        )
        print(f"\n[SUCCESS] Ingestion completed. {count} chunks persisted to vector store.")
    except Exception as exc:
        logger.error(f"Ingestion failed: {exc}")
        print(f"\n[ERROR] Ingestion failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
