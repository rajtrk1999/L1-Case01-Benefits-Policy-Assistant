"""Grounded Q&A assistant for the Benefits Policy Assistant.

The assistant retrieves the most relevant policy chunks from ChromaDB and then
uses the native Portkey client to answer using only those excerpts as context.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List

from src.portkey_config import MODEL_NAME, get_portkey_client
from src.retriever import get_relevant_chunks


def _extract_policy_ids(chunks: List[Dict[str, Any]]) -> List[str]:
    ids: List[str] = []
    seen = set()
    for chunk in chunks:
        policy_id = chunk.get("policy_id")
        if policy_id and policy_id not in seen:
            ids.append(policy_id)
            seen.add(policy_id)
    return ids


def _build_context(chunks: List[Dict[str, Any]]) -> str:
    context_parts: List[str] = []
    for i, chunk in enumerate(chunks, start=1):
        policy_id = chunk.get("policy_id") or "UNKNOWN"
        section = chunk.get("section") or "General"
        text = (chunk.get("text") or "").strip()
        if not text:
            continue
        context_parts.append(
            f"[Chunk {i}] Policy ID: {policy_id} | Section: {section}\n{text}\n"
        )
    return "\n---\n".join(context_parts)


def _parse_message_content(response: Any) -> str:
    if response is None:
        return ""
    if isinstance(response, dict):
        choices = response.get("choices") or []
        if choices:
            choice = choices[0]
            if isinstance(choice, dict):
                message = choice.get("message") or {}
                content = message.get("content") if isinstance(message, dict) else None
                if content:
                    return str(content)
        return str(response)

    choices = getattr(response, "choices", None) or []
    if choices:
        choice = choices[0]
        message = getattr(choice, "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if content:
                return str(content)
    return str(response)


def answer_question(
    query: str,
    experiment_name: str = "baseline",
    top_k: int | None = None,
    system_prompt: str | None = None,
) -> Dict[str, Any]:
    """Answer a policy question using retrieved context and a grounded Portkey call.

    Returns:
        {
            "question": query,
            "answer": "...",
            "cited_policy_ids": ["POL-XXX", ...],
            "retrieved_chunks": [
                {"text": ..., "policy_id": ..., "page": ..., "section": ...},
                ...
            ],
        }
    """
    effective_top_k = top_k if top_k is not None else (8 if experiment_name == "improved" else 5)
    chunks = get_relevant_chunks(query, top_k=effective_top_k)
    context = _build_context(chunks)

    base_prompt = (
        "You are a careful benefits policy assistant. Use only the policy excerpts in the context. "
        "Do not invent facts or answer from outside knowledge. If the answer is not supported by the policy text, "
        "say so clearly and avoid guessing. "
        "When citing policy rules, include inline references in the form [POL-XXX]. "
        "Mention only policy IDs that appear in the provided excerpts.\n\n"
        f"Question: {query}\n\n"
        f"Context:\n{context}\n\n"
        "Answer in concise, employee-friendly language with explicit policy citations."
    )

    if experiment_name == "improved":
        improvement_instructions = (
            "Prioritize the current effective policy version when older and newer rules conflict. "
            "If a question is not directly answered by the provided excerpts, explicitly say the policy excerpts do not specify the answer and do not guess. "
            "If multiple policies apply, cite the governing one most directly relevant to the question."
        )
        prompt = f"{base_prompt}\n\n{improvement_instructions}"
    else:
        prompt = base_prompt

    if system_prompt:
        prompt = f"{system_prompt}\n\n{prompt}"

    client = get_portkey_client()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are a grounded benefits policy assistant."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=400,
        metadata={
            "experiment_name": experiment_name,
            "query_topic": "benefits_policy",
            "retrieval_window": str(effective_top_k),
        },
    )

    answer = _parse_message_content(response).strip()
    if not answer:
        answer = "I could not verify this from the policy handbook."

    # ensure the response is grounded by removing any unsupported fact claims when the context is empty
    if not chunks:
        answer = "I could not find supporting policy context for that question."

    cited_ids = list(dict.fromkeys(re.findall(r'POL-\d{3}', answer)))

    return {
        "question": query,
        "answer": answer,
        "cited_policy_ids": cited_ids,
        "retrieved_chunks": chunks,
    }


if __name__ == "__main__":
    sample = "I'm on the Bronze HDHP - how much does the company put into my HSA for family coverage?"
    result = answer_question(sample)
    print(json.dumps(result, indent=2, ensure_ascii=False))
