from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

import json
import time
from datetime import datetime
from uuid import uuid4
from pathlib import Path

from ai_agent import (
    assess_initiative,
    compare_assessments,
    get_embedding,
    cosine_similarity,
)
from schemas import (
    SavedAssessment,
    AssessmentComparisonRequest,
    HumanReviewItem,
    HumanReviewActionRequest,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path("data/assessments")
DATA_DIR.mkdir(parents=True, exist_ok=True)

REVIEW_DIR = Path("data/reviews")
REVIEW_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDINGS_DIR = Path("data/embeddings")
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

SESSION_MEMORY = []
MAX_SESSION_ITEMS = 5


class InitiativeRequest(BaseModel):
    initiative: str


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


def get_embedding_path(assessment_id: str) -> Path:
    return EMBEDDINGS_DIR / f"{assessment_id}.json"


def update_session_memory(saved: SavedAssessment):
    SESSION_MEMORY.insert(0, {
        "id": saved.id,
        "created_at": saved.created_at.isoformat(),
        "initiative": saved.initiative,
        "viability_score": saved.result.viability_score
    })
    del SESSION_MEMORY[MAX_SESSION_ITEMS:]


def save_embedding(assessment_id: str, initiative_text: str, embedding: list[float]):
    payload = {
        "assessment_id": assessment_id,
        "initiative": initiative_text,
        "embedding": embedding,
    }
    filepath = get_embedding_path(assessment_id)
    write_json_file(filepath, payload)


def load_all_embeddings():
    items = []

    for file in EMBEDDINGS_DIR.glob("*.json"):
        try:
            data = read_json_file(file)
            items.append(data)
        except Exception:
            continue

    return items


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


def find_similar_cases(current_initiative: str, limit: int = 3):
    assessments = load_all_assessments()
    similar = []

    review_lookup = {}

    for review_file in REVIEW_DIR.glob("*.json"):
        try:
            review_data = read_json_file(review_file)
            review_lookup[review_data["assessment_id"]] = review_data
        except Exception:
            continue

    for item in assessments:
        initiative_text = item.get("initiative", "")
        similarity = compute_simple_similarity(current_initiative, initiative_text)

        if similarity < 15:
            continue

        review_data = review_lookup.get(item["id"])

        similar.append({
            "assessment_id": item["id"],
            "created_at": item["created_at"],
            "initiative_excerpt": initiative_text[:220],
            "viability_score": item["result"]["viability_score"],
            "similarity_score": similarity,
            "review_status": review_data["status"] if review_data else None,
            "review_reason": review_data["review_reason"] if review_data else None,
        })

    similar.sort(key=lambda x: (-x["similarity_score"], -x["viability_score"]))
    return similar[:limit]


def find_similar_cases_semantic(current_initiative: str, limit: int = 3):
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

        if similarity_score < 55:
            continue

        review_data = review_lookup.get(assessment_id)

        similar.append({
            "assessment_id": assessment_id,
            "created_at": assessment["created_at"],
            "initiative_excerpt": assessment["initiative"][:220],
            "viability_score": assessment["result"]["viability_score"],
            "similarity_score": similarity_score,
            "review_status": review_data["status"] if review_data else None,
            "review_reason": review_data["review_reason"] if review_data else None,
        })

    similar.sort(key=lambda x: (-x["similarity_score"], -x["viability_score"]))
    return similar[:limit]


def find_similar_cases_hybrid(current_initiative: str, limit: int = 3):
    semantic_cases = find_similar_cases_semantic(current_initiative, limit=limit)

    if semantic_cases:
        return semantic_cases

    return find_similar_cases(current_initiative, limit=limit)


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


def compute_review_priority(saved) -> str:
    result = saved.result

    if not result.review_decision or not result.review_decision.requires_human_review:
        return "low"

    if result.scores:
        if result.scores.governance_risk >= 8 or result.scores.integration_effort >= 8:
            return "high"

    if result.review_decision.confidence_level == "low":
        return "high"

    return "medium"


def create_review_item(saved):
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


def save_assessment(initiative_text: str, result):
    saved = SavedAssessment(
        id=str(uuid4()),
        created_at=datetime.utcnow(),
        initiative=initiative_text,
        result=result
    )

    filepath = get_assessment_path(saved.id)
    write_json_file(filepath, saved.model_dump(mode="json"))

    update_session_memory(saved)

    try:
        embedding = get_embedding(initiative_text)
        save_embedding(saved.id, initiative_text, embedding)
    except Exception as e:
        log_event("EMBEDDING_SAVE_ERROR", f"id={saved.id} error={repr(e)}")

    return saved

def find_similar_cases_semantic(
    current_initiative: str,
    limit: int = 5,
    min_similarity: int = 55
) -> list[dict]:
    current_embedding = get_embedding(current_initiative)

    embeddings = load_all_embeddings()
    assessments = {
        item["id"]: item
        for item in load_all_assessments()
    }

    similar_cases = []

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

        similar_cases.append({
            "assessment_id": assessment_id,
            "created_at": assessment.get("created_at"),
            "viability_score": assessment.get("result", {}).get("viability_score"),
            "similarity_score": similarity_score,
            "initiative_excerpt": assessment.get("initiative", "")[:220],
            "review_status": None,
            "review_reason": "Semantic similarity calculated with embeddings and cosine similarity.",
        })

    similar_cases.sort(
        key=lambda x: (
            -x["similarity_score"],
            -(x["viability_score"] or 0)
        )
    )

    return similar_cases[:limit]


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


def find_similar_cases_simple(
    current_initiative: str,
    limit: int = 5,
    min_similarity: int = 15
) -> list[dict]:
    assessments = load_all_assessments()
    similar_cases = []

    for item in assessments:
        initiative_text = item.get("initiative", "")
        similarity_score = compute_simple_similarity(
            current_initiative,
            initiative_text
        )

        if similarity_score < min_similarity:
            continue

        similar_cases.append({
            "assessment_id": item["id"],
            "created_at": item.get("created_at"),
            "viability_score": item.get("result", {}).get("viability_score"),
            "similarity_score": similarity_score,
            "initiative_excerpt": initiative_text[:220],
            "review_status": None,
            "review_reason": "Fallback lexical similarity used because semantic search returned no results.",
        })

    similar_cases.sort(
        key=lambda x: (
            -x["similarity_score"],
            -(x["viability_score"] or 0)
        )
    )

    return similar_cases[:limit]



def find_similar_cases_hybrid(current_initiative: str, limit: int = 5) -> list[dict]:
    semantic_cases = find_similar_cases_semantic(
        current_initiative=current_initiative,
        limit=limit,
        min_similarity=55
    )

    if semantic_cases:
        return semantic_cases

    return find_similar_cases_simple(
        current_initiative=current_initiative,
        limit=limit,
        min_similarity=15
    )

def build_memory_summary(similar_cases: list[dict]) -> str:
    if not similar_cases:
        return "Nenhum caso histórico semelhante encontrado."

    parts = []

    for case in similar_cases:
        part = (
            f"Caso {case['assessment_id']} teve viability_score="
            f"{case.get('viability_score')} com similarity_score="
            f"{case.get('similarity_score')}."
        )

        if case.get("review_status"):
            part += f" Status de revisão: {case['review_status']}."

        parts.append(part)

    return " | ".join(parts)

@app.get("/")
def healthcheck():
    return {"status": "ok"}


@app.post("/assess")
def assess(request: InitiativeRequest):
    started = time.perf_counter()
    log_event("ASSESS_START", f"initiative_length={len(request.initiative)}")

    try:
        similar_cases = find_similar_cases_hybrid(request.initiative)
        memory_summary = build_memory_summary(similar_cases)

        result = assess_initiative(
            request.initiative,
            similar_cases=similar_cases,
            memory_summary=memory_summary
        )

        saved = save_assessment(request.initiative, result)
        review_item = create_review_item(saved)

        elapsed = time.perf_counter() - started
        log_event("ASSESS_SUCCESS", f"id={saved.id} elapsed={elapsed:.2f}s")

        return {
            "status": "success",
            "message": "Assessment created successfully",
            "data": saved.model_dump(mode="json"),
            "review": review_item.model_dump(mode="json") if review_item else None,
            "meta": {
                "elapsed_seconds": round(elapsed, 2)
            }
        }

    except Exception as e:
        elapsed = time.perf_counter() - started
        log_event("ASSESS_ERROR", f"error={repr(e)} elapsed={elapsed:.2f}s")
        raise HTTPException(status_code=500, detail=f"Failed to assess initiative: {str(e)}")


@app.post("/assess-file")
async def assess_file(file: UploadFile = File(...)):
    started = time.perf_counter()
    log_event("ASSESS_FILE_START", f"filename={file.filename}")

    allowed_extensions = {".txt", ".md"}
    suffix = Path(file.filename).suffix.lower()

    if suffix not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Formato de arquivo não suportado. Use .txt ou .md"
        )

    content = await file.read()

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível decodificar o arquivo como UTF-8"
        )

    initiative_text = f"""
O usuário enviou um documento contendo uma descrição de iniciativa de IA.

Extraia e avalie a iniciativa com foco em contexto enterprise.

Nome do arquivo: {file.filename}

Conteúdo do documento:
{text}
""".strip()

    try:
        similar_cases = find_similar_cases_hybrid(initiative_text)
        memory_summary = build_memory_summary(similar_cases)

        result = assess_initiative(
            initiative_text,
            similar_cases=similar_cases,
            memory_summary=memory_summary
        )

        saved = save_assessment(initiative_text, result)
        review_item = create_review_item(saved)

        elapsed = time.perf_counter() - started
        log_event("ASSESS_FILE_SUCCESS", f"id={saved.id} elapsed={elapsed:.2f}s")

        return {
            "status": "success",
            "message": "File assessed successfully",
            "data": saved.model_dump(mode="json"),
            "review": review_item.model_dump(mode="json") if review_item else None,
            "meta": {
                "elapsed_seconds": round(elapsed, 2),
                "filename": file.filename
            }
        }

    except Exception as e:
        elapsed = time.perf_counter() - started
        log_event("ASSESS_FILE_ERROR", f"error={repr(e)} elapsed={elapsed:.2f}s")
        raise HTTPException(status_code=500, detail=f"Failed to assess file: {str(e)}")


@app.get("/assessments")
def list_assessments():
    log_event("LIST_ASSESSMENTS_START")

    try:
        items = []

        for file in sorted(DATA_DIR.glob("*.json"), reverse=True):
            data = read_json_file(file)
            items.append({
                "id": data["id"],
                "created_at": data["created_at"],
                "initiative": data["initiative"],
                "viability_score": data["result"]["viability_score"]
            })

        log_event("LIST_ASSESSMENTS_SUCCESS", f"count={len(items)}")

        return {
            "status": "success",
            "data": items
        }

    except Exception as e:
        log_event("LIST_ASSESSMENTS_ERROR", f"error={repr(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list assessments: {str(e)}")


@app.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: str):
    log_event("GET_ASSESSMENT_START", f"id={assessment_id}")

    try:
        filepath = ensure_assessment_exists(assessment_id)
        data = read_json_file(filepath)

        log_event("GET_ASSESSMENT_SUCCESS", f"id={assessment_id}")

        return {
            "status": "success",
            "data": data
        }

    except HTTPException:
        log_event("GET_ASSESSMENT_NOT_FOUND", f"id={assessment_id}")
        raise

    except Exception as e:
        log_event("GET_ASSESSMENT_ERROR", f"id={assessment_id} error={repr(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to load assessment: {str(e)}")


@app.post("/compare")
def compare(request: AssessmentComparisonRequest):
    started = time.perf_counter()
    log_event("COMPARE_START", f"current_id={request.current_id} previous_id={request.previous_id}")

    try:
        current_path = ensure_assessment_exists(request.current_id)
        previous_path = ensure_assessment_exists(request.previous_id)

        current_data = read_json_file(current_path)
        previous_data = read_json_file(previous_path)

        comparison = compare_assessments(
            current_assessment=current_data,
            previous_assessment=previous_data
        )

        elapsed = time.perf_counter() - started
        log_event("COMPARE_SUCCESS", f"elapsed={elapsed:.2f}s")

        return {
            "status": "success",
            "data": comparison.model_dump(),
            "meta": {
                "elapsed_seconds": round(elapsed, 2)
            }
        }

    except HTTPException:
        log_event("COMPARE_NOT_FOUND")
        raise

    except Exception as e:
        elapsed = time.perf_counter() - started
        log_event("COMPARE_ERROR", f"error={repr(e)} elapsed={elapsed:.2f}s")
        raise HTTPException(status_code=500, detail=f"Failed to compare assessments: {str(e)}")


@app.get("/session-context")
def get_session_context():
    log_event("SESSION_CONTEXT_READ", f"count={len(SESSION_MEMORY)}")
    return {
        "status": "success",
        "data": SESSION_MEMORY
    }


@app.get("/reviews")
def list_reviews():
    try:
        items = []

        for file in sorted(REVIEW_DIR.glob("*.json"), reverse=True):
            data = read_json_file(file)
            items.append(data)

        priority_order = {"high": 0, "medium": 1, "low": 2}
        status_order = {"new": 0, "in_review": 1, "approved": 2, "rejected": 3}

        items.sort(
            key=lambda x: (
                status_order.get(x["status"], 99),
                priority_order.get(x["priority"], 99),
                x["created_at"]
            )
        )

        return {
            "status": "success",
            "data": items
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list reviews: {str(e)}")


@app.get("/reviews/{review_id}")
def get_review(review_id: str):
    try:
        filepath = ensure_review_exists(review_id)
        data = read_json_file(filepath)

        return {
            "status": "success",
            "data": data
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load review item: {str(e)}")


@app.post("/reviews/{review_id}/action")
def review_action(review_id: str, request: HumanReviewActionRequest):
    try:
        filepath = ensure_review_exists(review_id)
        data = read_json_file(filepath)

        if request.action not in {"in_review", "approved", "rejected"}:
            raise HTTPException(status_code=400, detail="Invalid review action")

        data["status"] = request.action
        data["assigned_to"] = request.reviewer_name
        data["resolution_note"] = request.resolution_note

        if request.action in {"approved", "rejected"}:
            data["resolved_at"] = datetime.utcnow().isoformat()

        write_json_file(filepath, data)

        return {
            "status": "success",
            "message": "Review updated successfully",
            "data": data
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update review item: {str(e)}")


@app.post("/memory/search")
def memory_search(request: InitiativeRequest):
    try:
        similar_cases = find_similar_cases_hybrid(request.initiative)
        memory_summary = build_memory_summary(similar_cases)

        return {
            "status": "success",
            "data": {
                "similar_cases": similar_cases,
                "memory_summary": memory_summary
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search memory: {str(e)}")


@app.post("/memory/search-semantic")
def memory_search_semantic(request: InitiativeRequest):
    try:
        similar_cases = find_similar_cases_semantic(request.initiative)
        memory_summary = build_memory_summary(similar_cases)

        return {
            "status": "success",
            "data": {
                "similar_cases": similar_cases,
                "memory_summary": memory_summary
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search semantic memory: {str(e)}")