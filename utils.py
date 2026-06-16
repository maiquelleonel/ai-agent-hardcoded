import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import HTTPException
from openai import OpenAI

from constants import (
    DATA_DIR,
    DB_FILE,
    EMBEDDINGS_DIR,
    MAX_SESSION_ITEMS,
    REVIEW_DIR,
    SESSION_MEMORY,
)
from schemas import HumanReviewItem, SavedAssessment


def save_assessments(items):
    with DB_FILE.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


# Carrega variáveis de ambiente e configura o cliente OpenAI
load_dotenv()
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5")
client = OpenAI()


def log_event(event: str, details: str = ""):
    timestamp = datetime.utcnow().isoformat()
    print(f"[{timestamp}] {event} {details}".strip())


def read_json_file(filepath: Path):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_file(filepath: Path, payload: dict):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def get_embedding_path(assessment_id: str) -> Path:
    return EMBEDDINGS_DIR / f"{assessment_id}.json"


def save_embedding(assessment_id: str, initiative_text: str, embedding: list[float]):
    payload = {
        "assessment_id": assessment_id,
        "initiative": initiative_text,
        "embedding": embedding,
    }
    filepath = get_embedding_path(assessment_id)
    write_json_file(filepath, payload)


def load_all_embeddings() -> list[dict]:
    items = []
    for file in EMBEDDINGS_DIR.glob("*.json"):
        try:
            data = read_json_file(file)
            items.append(data)
        except Exception:
            continue
    return items


def get_assessment_path(assessment_id: str) -> Path:
    return DATA_DIR / f"{assessment_id}.json"


def ensure_assessment_exists(assessment_id: str) -> Path:
    filepath = get_assessment_path(assessment_id)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Assessment not found")
    return filepath


def get_review_path(review_id: str) -> Path:
    return REVIEW_DIR / f"{review_id}.json"


def ensure_review_exists(review_id: str) -> Path:
    filepath = get_review_path(review_id)
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Review item not found")
    return filepath


def update_session_memory(saved: SavedAssessment):
    SESSION_MEMORY.insert(
        0,
        {
            "id": saved.id,
            "created_at": saved.created_at.isoformat(),
            "initiative": saved.initiative,
            "viability_score": saved.result.viability_score,
        },
    )
    del SESSION_MEMORY[MAX_SESSION_ITEMS:]


def load_all_assessments():
    items = []
    for file in DATA_DIR.glob("*.json"):
        try:
            data = read_json_file(file)
            items.append(data)
        except Exception:
            continue
    return items


def tokenize_text(text: str) -> set[str]:
    tokens = set()
    for token in text.lower().replace(",", " ").replace(".", " ").split():
        token = token.strip()
        if len(token) >= 3:
            tokens.add(token)
    return tokens


def compute_simple_similarity(text_a: str, text_b: str) -> int:
    tokens_a = tokenize_text(text_a)
    tokens_b = tokenize_text(text_b)

    if not tokens_a or not tokens_b:
        return 0

    intersection = len(tokens_a.intersection(tokens_b))
    union = len(tokens_a.union(tokens_b))

    if union == 0:
        return 0

    return round((intersection / union) * 100)


def find_assessment_by_id(assessment_id: str):
    assessments = load_all_assessments()
    for item in assessments:
        if item["id"] == assessment_id:
            return item
    return None


def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(model="text-embedding-3-small", input=text)
    return response.data[0].embedding


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def detect_initiative_type(description: str) -> str:
    text = description.lower()

    if any(term in text for term in ["rh", "ti", "atendimento interno", "help desk", "service desk", "colaborador"]):
        return "internal_copilot"

    if any(term in text for term in ["contrato", "cláusula", "jurídico", "fornecedor", "compliance contratual"]):
        return "contract_analysis"

    if any(term in text for term in ["crm", "lead", "pipeline", "vendas", "oportunidade comercial"]):
        return "sales_ai"

    if any(term in text for term in ["sensor", "falha", "equipamento", "manutenção preditiva", "iot"]):
        return "predictive_maintenance"

    if any(term in text for term in ["documento", "base de conhecimento", "faq", "política interna", "pdf"]):
        return "knowledge_assistant"

    return "generic_ai_initiative"


def get_recommended_stack(initiative_type: str) -> list[str]:
    stacks = {
        "internal_copilot": [
            "LLM provider",
            "RAG over internal documents",
            "API integration with ITSM/HR systems",
            "SSO/identity integration",
            "observability and audit logs",
        ],
        "contract_analysis": [
            "LLM provider",
            "document ingestion pipeline",
            "RAG over legal templates and policies",
            "human-in-the-loop review",
            "audit trail",
        ],
        "sales_ai": ["LLM provider", "CRM integration", "business rules layer", "analytics dashboard", "observability"],
        "predictive_maintenance": [
            "time series data pipeline",
            "ML models for anomaly detection",
            "sensor/IoT integration",
            "alerting workflow",
            "operations dashboard",
        ],
        "knowledge_assistant": [
            "LLM provider",
            "document ingestion pipeline",
            "embeddings and vector store",
            "retrieval layer",
            "usage monitoring",
        ],
        "generic_ai_initiative": [
            "LLM provider",
            "application backend",
            "data access layer",
            "logging and monitoring",
            "security controls",
        ],
    }
    return stacks.get(initiative_type, stacks["generic_ai_initiative"])


def get_common_risks(initiative_type: str) -> list[str]:
    risks = {
        "internal_copilot": [
            "hallucination in employee-facing answers",
            "exposure of internal information",
            "weak integration with internal processes",
            "poor knowledge base quality",
        ],
        "contract_analysis": [
            "false negatives in risk detection",
            "legal overreliance without human review",
            "sensitive document exposure",
            "inconsistent clause interpretation",
        ],
        "sales_ai": [
            "biased prioritization",
            "poor CRM data quality",
            "low trust from sales teams",
            "weak explainability of recommendations",
        ],
        "predictive_maintenance": [
            "poor sensor data quality",
            "high false positive rate",
            "integration difficulty with operational systems",
            "long time to prove ROI",
        ],
        "knowledge_assistant": [
            "stale documents",
            "irrelevant retrieval",
            "hallucinated answers",
            "missing access control",
        ],
        "generic_ai_initiative": [
            "unclear business objective",
            "weak data foundation",
            "lack of governance",
            "underestimated integration complexity",
        ],
    }
    return risks.get(initiative_type, risks["generic_ai_initiative"])


def build_memory_summary(similar_cases: list[dict]) -> str:
    if not similar_cases:
        return "No similar historical cases found."

    parts = []
    for case in similar_cases:
        part = (
            f"Case {case['assessment_id']} had viability_score={case['viability_score']} "
            f"with similarity_score={case['similarity_score']}"
        )
        if case.get("review_status"):
            part += f" and review_status={case['review_status']}"
        parts.append(part)

    return " | ".join(parts)


def compute_review_priority(saved: SavedAssessment) -> str:
    result = saved.result

    if not result.review_decision or not result.review_decision.requires_human_review:
        return "low"

    if result.scores:
        if result.scores.governance_risk >= 8 or result.scores.integration_effort >= 8:
            return "high"

    if result.review_decision.confidence_level == "low":
        return "high"

    return "medium"


def create_review_item(saved: SavedAssessment):
    result = saved.result

    if not result.review_decision or not result.review_decision.requires_human_review:
        return None

    review = HumanReviewItem(
        review_id=str(uuid4()),
        assessment_id=saved.id,
        created_at=datetime.utcnow(),
        priority=compute_review_priority(saved),
        status="new",
        review_reason=result.review_decision.review_reason,
        confidence_level=result.review_decision.confidence_level,
    )
    filepath = get_review_path(review.review_id)
    write_json_file(filepath, review.model_dump(mode="json"))
    return review


def save_assessment(
    initiative_text: str, result: Any
):  # Usando Any para evitar circular import com InitiativeAssessment
    saved = SavedAssessment(id=str(uuid4()), created_at=datetime.utcnow(), initiative=initiative_text, result=result)
    filepath = get_assessment_path(saved.id)
    write_json_file(filepath, saved.model_dump(mode="json"))
    update_session_memory(saved)

    try:
        embedding = get_embedding(initiative_text)
        save_embedding(saved.id, initiative_text, embedding)
    except Exception as e:
        log_event("EMBEDDING_SAVE_ERROR", f"id={saved.id} error={repr(e)}")

    return saved


def find_similar_cases_semantic(current_initiative: str, limit: int = 5, min_similarity: int = 55):
    current_embedding = get_embedding(current_initiative)
    embeddings = load_all_embeddings()
    assessments = {item["id"]: item for item in load_all_assessments()}

    review_lookup = {}
    for review_file in REVIEW_DIR.glob("*.json"):
        try:
            review_data = read_json_file(review_file)
            review_lookup[review_data["assessment_id"]] = review_data
        except Exception:
            continue

    similar = []

    for item in embeddings:
        assessment_id = item.get("assessment_id")
        stored_embedding = item.get("embedding")

        if not assessment_id or not stored_embedding:
            continue

        assessment = assessments.get(assessment_id)
        if not assessment:
            continue

        similarity = cosine_similarity(current_embedding, stored_embedding)
        similarity_score = round(similarity * 100)

        if similarity_score < min_similarity:
            continue

        review_data = review_lookup.get(assessment_id)

        similar.append(
            {
                "assessment_id": assessment_id,
                "created_at": assessment["created_at"],
                "initiative_excerpt": assessment["initiative"][:220],
                "viability_score": assessment["result"]["viability_score"],
                "similarity_score": similarity_score,
                "review_status": review_data["status"] if review_data else None,
                "review_reason": review_data["review_reason"] if review_data else None,
            }
        )

    similar.sort(key=lambda x: (-x["similarity_score"], -x["viability_score"]))
    return similar[:limit]


def find_similar_cases_simple(current_initiative: str, limit: int = 5, min_similarity: int = 15) -> list[dict]:
    assessments = load_all_assessments()
    similar_cases = []

    for item in assessments:
        initiative_text = item.get("initiative", "")
        similarity_score = compute_simple_similarity(current_initiative, initiative_text)

        if similarity_score < min_similarity:
            continue

        similar_cases.append(
            {
                "assessment_id": item["id"],
                "created_at": item.get("created_at"),
                "viability_score": item.get("result", {}).get("viability_score"),
                "similarity_score": similarity_score,
                "initiative_excerpt": initiative_text[:220],
                "review_status": None,
                "review_reason": "Fallback lexical similarity used because semantic search returned no results.",
            }
        )

    similar_cases.sort(key=lambda x: (-x["similarity_score"], -(x["viability_score"] or 0)))

    return similar_cases[:limit]


def find_similar_cases_hybrid(current_initiative: str, limit: int = 5) -> list[dict]:
    semantic_cases = find_similar_cases_semantic(current_initiative=current_initiative, limit=limit, min_similarity=55)

    if semantic_cases:
        return semantic_cases

    return find_similar_cases_simple(current_initiative=current_initiative, limit=limit, min_similarity=15)
