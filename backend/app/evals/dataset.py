from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class GoldenDocumentSpec:
    key: str
    title: str
    content: str
    mime_type: str = "text/plain"


@dataclass(slots=True)
class GoldenCaseSpec:
    name: str
    question: str
    expected_document_keys: list[str]
    expected_chunk_indices: list[int]
    expected_abstain: bool
    citation_constraints: dict[str, Any]
    tags: list[str]
    difficulty: str | None
    scenario_type: str | None
    top_k: int | None = None
    score_threshold: float | None = None


@dataclass(slots=True)
class GoldenDataset:
    name: str
    description: str | None
    documents: list[GoldenDocumentSpec]
    cases: list[GoldenCaseSpec]


def _resolve_dataset_path(*, dataset: str, dataset_dir: str, dataset_path: str | None) -> Path:
    if dataset_path:
        path = Path(dataset_path)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path

    return (Path.cwd() / dataset_dir / f"{dataset}.json").resolve()


def load_golden_dataset(*, dataset: str, dataset_dir: str, dataset_path: str | None = None) -> GoldenDataset:
    path = _resolve_dataset_path(dataset=dataset, dataset_dir=dataset_dir, dataset_path=dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"golden dataset not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    documents = payload.get("documents", [])
    cases = payload.get("cases", [])

    dataset_name = str(payload.get("dataset", dataset)).strip()
    if not dataset_name:
        raise ValueError("dataset name is required")

    parsed_docs: list[GoldenDocumentSpec] = []
    seen_doc_keys: set[str] = set()
    for row in documents:
        key = str(row.get("key", "")).strip()
        title = str(row.get("title", "")).strip()
        content = str(row.get("content", "")).strip()
        mime_type = str(row.get("mime_type", "text/plain")).strip() or "text/plain"
        if not key or not title or not content:
            raise ValueError("dataset document requires key/title/content")
        if key in seen_doc_keys:
            raise ValueError(f"duplicated document key: {key}")
        seen_doc_keys.add(key)
        parsed_docs.append(GoldenDocumentSpec(key=key, title=title, content=content, mime_type=mime_type))

    parsed_cases: list[GoldenCaseSpec] = []
    seen_case_names: set[str] = set()
    for row in cases:
        name = str(row.get("name", "")).strip()
        question = str(row.get("question", "")).strip()
        if not name or not question:
            raise ValueError("dataset case requires name/question")
        if name in seen_case_names:
            raise ValueError(f"duplicated case name: {name}")
        seen_case_names.add(name)

        expected_document_keys = [str(item).strip() for item in row.get("expected_document_keys", []) if str(item).strip()]
        expected_chunk_indices = [int(item) for item in row.get("expected_chunk_indices", [])]
        expected_abstain = bool(row.get("expected_abstain", False))
        citation_constraints = dict(row.get("citation_constraints", {}))
        tags = [str(item).strip() for item in row.get("tags", []) if str(item).strip()]
        difficulty = row.get("difficulty")
        scenario_type = row.get("scenario_type")
        top_k = int(row["top_k"]) if "top_k" in row and row["top_k"] is not None else None
        score_threshold = (
            float(row["score_threshold"])
            if "score_threshold" in row and row["score_threshold"] is not None
            else None
        )

        missing_keys = [key for key in expected_document_keys if key not in seen_doc_keys]
        if missing_keys:
            raise ValueError(f"case '{name}' references unknown document keys: {missing_keys}")

        parsed_cases.append(
            GoldenCaseSpec(
                name=name,
                question=question,
                expected_document_keys=expected_document_keys,
                expected_chunk_indices=expected_chunk_indices,
                expected_abstain=expected_abstain,
                citation_constraints=citation_constraints,
                tags=tags,
                difficulty=str(difficulty) if difficulty is not None else None,
                scenario_type=str(scenario_type) if scenario_type is not None else None,
                top_k=top_k,
                score_threshold=score_threshold,
            )
        )

    if not parsed_cases:
        raise ValueError("dataset cases cannot be empty")

    return GoldenDataset(
        name=dataset_name,
        description=payload.get("description"),
        documents=parsed_docs,
        cases=parsed_cases,
    )
