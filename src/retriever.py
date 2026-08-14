"""Retrieval utilities for Benefits Policy Assistant using ChromaDB."""
from typing import List, Dict
import os

import chromadb

CHROMA_DIR = os.path.abspath("./chroma_db")
COLLECTION_NAME = "benefits_policies"


def _get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        col = client.get_collection(name=COLLECTION_NAME)
    except Exception:
        col = client.get_or_create_collection(name=COLLECTION_NAME)
    return col


def get_relevant_chunks(query: str, top_k: int = 3) -> List[Dict]:
    """Query ChromaDB and return top_k chunks with metadata.

    Returns a list of dicts: {"text": ..., "policy_id": ..., "page": ..., "section": ...}
    """
    col = _get_collection()
    res = col.query(query_texts=[query], n_results=top_k)
    out = []
    # chroma returns documents as list of lists
    docs = res.get("documents", [[]])[0]
    metadatas = res.get("metadatas", [[]])[0]
    for doc, md in zip(docs, metadatas):
        out.append({
            "text": doc,
            "policy_id": md.get("policy_id"),
            "page": md.get("page"),
            "section": md.get("section"),
            "source": md.get("source"),
        })
    return out
