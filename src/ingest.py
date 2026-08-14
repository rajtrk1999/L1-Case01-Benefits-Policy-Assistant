"""Document ingestion for Benefits Policy Assistant.

Loads PDF/MD/TXT files from the `data/` directory, chunks text, extracts
simple structural metadata, and persists embeddings into a local ChromaDB
store at `./chroma_db`.
"""
from typing import List, Dict, Tuple, Optional
import os
import re
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import chromadb
from chromadb.utils import embedding_functions

try:
    from pypdf import PdfReader
except Exception:
    # pypdf earlier provided as `pypdf` in requirements
    from PyPDF2 import PdfReader  # type: ignore


CHROMA_DIR = os.path.abspath("./chroma_db")
COLLECTION_NAME = "benefits_policies"


def _read_file_text(path: Path) -> Tuple[str, List[int]]:
    """Return full text and an optional list of page start indices.

    For PDFs the second return value is a list mapping page index -> char
    offset in the concatenated text so callers can infer page numbers.
    For txt/md files, an empty list is returned.
    """
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        pages = []
        parts = []
        offset = 0
        for p in reader.pages:
            text = p.extract_text() or ""
            parts.append(text)
            pages.append(offset)
            offset += len(text)
        return "\n".join(parts), pages

    # md or txt
    text = path.read_text(encoding="utf-8", errors="ignore")
    return text, []


def _find_headings(text: str) -> List[Tuple[int, str]]:
    """Return list of (char_index, heading_title) for approximate headings.

    - For markdown, uses lines starting with '#'
    - Otherwise finds ALL CAPS short lines or lines that start with 'Section'/'Chapter'
    """
    headings = []
    lines = text.splitlines()
    pos = 0
    for ln in lines:
        stripped = ln.strip()
        # Markdown heading
        m = re.match(r"^(#+)\s*(.*)$", stripped)
        if m:
            title = m.group(2).strip()
            headings.append((pos, title))
        else:
            # ALL CAPS heuristic
            if len(stripped) > 0 and len(stripped) < 100 and stripped.isupper():
                headings.append((pos, stripped))
            elif re.match(r"^(Section|Chapter|Policy)[:\s].+", stripped, re.I):
                headings.append((pos, stripped))
        pos += len(ln) + 1
    return headings


def _get_section_for_index(headings: List[Tuple[int, str]], idx: int) -> Optional[str]:
    last = None
    for pos, title in headings:
        if pos <= idx:
            last = title
        else:
            break
    return last


def _extract_policy_id(text: str) -> Optional[str]:
    """Extract the most relevant policy ID from a chunk.

    Chunks are often split across section boundaries, so if a chunk contains more
    than one policy heading we prefer the last one, which is typically the most
    relevant section within the chunk.
    """
    m = re.search(r"Policy\s*ID[:#\-\s]*([A-Z0-9-_]+)", text, re.I)
    if m:
        return m.group(1)

    matches = re.findall(r"\b(POL-\d{3,})\b", text, re.I)
    if matches:
        return matches[-1].upper()
    return None


def _split_markdown_sections(text: str) -> List[Tuple[str, str, str]]:
    """Split markdown by section headers and return (policy_id, section_title, section_text)."""
    sections: List[Tuple[str, str, str]] = []
    current_policy_id: Optional[str] = None
    current_section = ""
    current_lines: List[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        m = re.match(r"^##\s*(POL-\d+)\s*(.*)$", line)
        if m:
            if current_policy_id and current_lines:
                sections.append((current_policy_id, current_section, "\n".join(current_lines).strip()))
            current_policy_id = m.group(1).upper()
            current_section = (m.group(2).strip() or current_policy_id).strip()
            current_lines = [raw_line]
        elif current_policy_id:
            current_lines.append(raw_line)

    if current_policy_id and current_lines:
        sections.append((current_policy_id, current_section, "\n".join(current_lines).strip()))

    return sections


def _chunk_markdown_section(section_text: str, chunk_size: int = 500) -> List[str]:
    """Break a markdown policy section into sentence-safe chunks without mid-sentence cuts."""
    text = section_text.strip()
    if not text:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: List[str] = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if not current:
            current = sentence
            continue
        if len(current) + 1 + len(sentence) <= chunk_size:
            current = f"{current} {sentence}"
            continue
        chunks.append(current.strip())
        current = sentence

    if current:
        chunks.append(current.strip())

    # If a single sentence is longer than the target, split on word boundaries.
    final_chunks: List[str] = []
    for chunk in chunks:
        if len(chunk) <= chunk_size:
            final_chunks.append(chunk)
            continue
        words = chunk.split()
        temp = ""
        for word in words:
            candidate = f"{temp} {word}".strip()
            if not temp:
                temp = word
            elif len(candidate) <= chunk_size:
                temp = candidate
            else:
                final_chunks.append(temp)
                temp = word
        if temp:
            final_chunks.append(temp)
    return final_chunks if final_chunks else chunks


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[Tuple[str, int]]:
    """Chunk text by markdown section when available, otherwise fallback to naive character splitting."""
    if re.search(r"(?m)^##\s*POL-\d+", text):
        sections = _split_markdown_sections(text)
        chunks: List[Tuple[str, int]] = []
        offset = 0
        for _, _, section_text in sections:
            for part in _chunk_markdown_section(section_text, chunk_size=chunk_size):
                chunks.append((part, offset))
                offset += len(part)
        return chunks

    chunks = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + chunk_size, n)
        chunk = text[i:end]
        chunks.append((chunk, i))
        if end == n:
            break
        i = end - overlap
    return chunks


def ingest_directory(data_dir: str = "data") -> None:
    data_path = Path(data_dir)
    files = list(data_path.glob("**/*"))
    files = [f for f in files if f.suffix.lower() in (".pdf", ".md", ".txt")]

    # Use ChromaDB's default embedding function to keep the baseline simple and
    # local; if an OpenAI key is present, the default function may not be used.
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    emb_fn = embedding_functions.DefaultEmbeddingFunction()
    collection = client.get_or_create_collection(name=COLLECTION_NAME, embedding_function=emb_fn)

    docs = []
    metadatas = []
    ids = []

    doc_id_ctr = 0
    for f in files:
        text, page_starts = _read_file_text(f)
        headings = _find_headings(text)

        if f.suffix.lower() == ".md" and re.search(r"(?m)^##\s*POL-\d+", text):
            section_chunks = _split_markdown_sections(text)
            for policy_id, section, section_text in section_chunks:
                for chunk_value in _chunk_markdown_section(section_text):
                    resolved = f.resolve()
                    try:
                        source_value = str(resolved.relative_to(Path.cwd()))
                    except ValueError:
                        source_value = str(resolved)

                    metadata = {
                        "source": source_value,
                        "page": "",
                        "section": section,
                        "policy_id": policy_id,
                    }
                    docs.append(chunk_value)
                    metadatas.append(metadata)
                    ids.append(f"doc-{doc_id_ctr}")
                    doc_id_ctr += 1
            continue

        chunks = chunk_text(text)
        for chunk_value, start_idx in chunks:
            page = None
            if page_starts:
                # find page index by last page_start <= start_idx
                page = max([i for i, p in enumerate(page_starts) if p <= start_idx]) + 1 if any(p <= start_idx for p in page_starts) else None

            section = _get_section_for_index(headings, start_idx)
            policy_id = _extract_policy_id(chunk_value)

            resolved = f.resolve()
            try:
                source_value = str(resolved.relative_to(Path.cwd()))
            except ValueError:
                source_value = str(resolved)

            metadata = {
                "source": source_value,
                "page": page if page is not None else "",
                "section": section if section is not None else "",
                "policy_id": policy_id if policy_id is not None else "",
            }
            docs.append(chunk_value)
            metadatas.append(metadata)
            ids.append(f"doc-{doc_id_ctr}")
            doc_id_ctr += 1

    if docs:
        # upsert into chroma collection
        collection.add(documents=docs, metadatas=metadatas, ids=ids)
        print(f"Ingested {len(docs)} chunks into collection '{COLLECTION_NAME}' at {CHROMA_DIR}")
    else:
        print("No documents found to ingest.")


def main():
    import argparse

    p = argparse.ArgumentParser(description="Ingest policy documents into local ChromaDB")
    p.add_argument("--data_dir", default="data")
    args = p.parse_args()
    ingest_directory(args.data_dir)


if __name__ == "__main__":
    main()
