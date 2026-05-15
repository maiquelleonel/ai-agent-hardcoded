import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from ai_agent import assess_initiative


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = Path("assessments.json")


class AssessRequest(BaseModel):
    initiative: str

class CompareRequest(BaseModel):
    current_id: str
    previous_id: str

def find_assessment_by_id(assessment_id: str):
    assessments = load_assessments()

    for item in assessments:
        if item["id"] == assessment_id:
            return item

    return None

@app.post("/compare")
def compare_assessments(request: CompareRequest):
    current = find_assessment_by_id(request.current_id)
    previous = find_assessment_by_id(request.previous_id)

    if not current:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment atual não encontrado: {request.current_id}"
        )

    if not previous:
        raise HTTPException(
            status_code=404,
            detail=f"Assessment anterior não encontrado: {request.previous_id}"
        )

    current_result = current.get("result", {})
    previous_result = previous.get("result", {})

    current_score = current.get("viability_score")
    previous_score = previous.get("viability_score")

    major_differences = []

    if current_score is not None and previous_score is not None:
        diff = current_score - previous_score

        if diff > 0:
            major_differences.append(
                f"A avaliação atual tem viabilidade superior em {diff} ponto(s): "
                f"{current_score}/10 contra {previous_score}/10."
            )
        elif diff < 0:
            major_differences.append(
                f"A avaliação atual tem viabilidade inferior em {abs(diff)} ponto(s): "
                f"{current_score}/10 contra {previous_score}/10."
            )
        else:
            major_differences.append(
                f"As duas avaliações possuem a mesma nota de viabilidade: {current_score}/10."
            )

    current_complexity = current_result.get("technical_complexity", "")
    previous_complexity = previous_result.get("technical_complexity", "")

    if current_complexity != previous_complexity:
        major_differences.append(
            "As avaliações apresentam diferenças na complexidade técnica percebida."
        )

    current_risks = current_result.get("main_risks", [])
    previous_risks = previous_result.get("main_risks", [])

    if len(current_risks) != len(previous_risks):
        major_differences.append(
            f"A avaliação atual possui {len(current_risks)} risco(s) principal(is), "
            f"enquanto a anterior possui {len(previous_risks)}."
        )

    current_stack = current_result.get("initial_stack", [])
    previous_stack = previous_result.get("initial_stack", [])

    if current_stack != previous_stack:
        major_differences.append(
            "As stacks iniciais sugeridas apresentam diferenças relevantes."
        )

    if not major_differences:
        major_differences.append(
            "Não foram identificadas diferenças relevantes entre as duas avaliações."
        )

    summary = (
        "A comparação analisou as duas iniciativas considerando nota de viabilidade, "
        "complexidade técnica, riscos principais, quick wins e stack inicial sugerida. "
        f"A avaliação atual possui score {current_score}/10 e a avaliação anterior "
        f"possui score {previous_score}/10."
    )

    if current_score is not None and previous_score is not None:
        if current_score > previous_score:
            recommendation = (
                "Priorizar a iniciativa atual, pois ela apresenta maior viabilidade relativa. "
                "Recomenda-se validar dependências técnicas, riscos e quick wins antes da execução."
            )
        elif current_score < previous_score:
            recommendation = (
                "Reavaliar a iniciativa atual antes de priorizá-la, pois a avaliação anterior "
                "apresenta maior viabilidade. Recomenda-se revisar escopo, riscos e esforço técnico."
            )
        else:
            recommendation = (
                "As duas iniciativas apresentam viabilidade equivalente. A decisão deve considerar "
                "valor de negócio, urgência estratégica, disponibilidade de dados e capacidade de execução."
            )
    else:
        recommendation = (
            "Não foi possível comparar scores de viabilidade. Recomenda-se revisar os dados persistidos "
            "das avaliações antes de tomar uma decisão."
        )

    return {
        "data": {
            "summary": summary,
            "major_differences": major_differences,
            "recommendation": recommendation
        }
    }

@app.post("/memory/search-semantic")
def memory_search_semantic(request: InitiativeRequest):
    try:
        text_to_search = request.initiative.strip()

        if not text_to_search:
            raise HTTPException(
                status_code=400,
                detail="Texto de busca vazio."
            )

        similar_cases = find_similar_cases_semantic(
            current_initiative=text_to_search,
            limit=5,
            min_similarity=55
        )

        memory_summary = build_memory_summary(similar_cases)

        return {
            "status": "success",
            "data": {
                "memory_summary": memory_summary,
                "similar_cases": similar_cases,
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na busca semântica: {str(e)}"
        )

@app.post("/memory/search")
def memory_search(request: InitiativeRequest):
    try:
        text_to_search = request.initiative.strip()

        if not text_to_search:
            raise HTTPException(
                status_code=400,
                detail="Texto de busca vazio."
            )

        similar_cases = find_similar_cases_hybrid(
            current_initiative=text_to_search,
            limit=5
        )

        memory_summary = build_memory_summary(similar_cases)

        return {
            "status": "success",
            "data": {
                "memory_summary": memory_summary,
                "similar_cases": similar_cases,
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro na busca de memória: {str(e)}"
        )

def load_assessments():
    if not DB_FILE.exists():
        return []

    try:
        with DB_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_assessments(items):
    with DB_FILE.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

@app.post("/assess-file")
async def assess_file(file: UploadFile = File(...)):
    try:
        if not file.filename.lower().endswith((".txt", ".md")):
            raise HTTPException(
                status_code=400,
                detail="Formato inválido. Envie apenas arquivos .txt ou .md."
            )

        content_bytes = await file.read()
        initiative_text = content_bytes.decode("utf-8").strip()

        if not initiative_text:
            raise HTTPException(
                status_code=400,
                detail="O arquivo está vazio."
            )

        result = assess_initiative(initiative_text)

        assessments = load_assessments()
        result_dict = result.model_dump()

        memory_summary = (
            f"A memória local contém {len(assessments)} avaliações anteriores persistidas. "
            "Essas avaliações podem ser usadas como referência para comparar iniciativas, "
            "identificar padrões de risco, reaproveitar stacks sugeridas e melhorar a qualidade "
            "das próximas análises."
        )

        similar_cases = [
            {
                "assessment_id": item["id"],
                "viability_score": item.get("viability_score"),
                "similarity_score": 75,
                "review_status": "historical_reference",
                "review_reason": "Caso anterior disponível na memória local.",
                "initiative_excerpt": item.get("initiative", "")[:180],
            }
            for item in assessments[:3]
        ]

        result_dict["memory_context"] = {
            "memory_summary": memory_summary,
            "similar_cases": similar_cases,
        }

        saved_assessment = {
            "id": str(uuid4()),
            "initiative": initiative_text,
            "source_file": file.filename,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "viability_score": result.viability_score,
            "result": result_dict,
        }

        assessments.insert(0, saved_assessment)
        save_assessments(assessments)

        return {"data": saved_assessment}

    except HTTPException:
        raise

    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível ler o arquivo. Salve o arquivo como UTF-8."
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao avaliar arquivo: {str(e)}"
        )

@app.get("/")
def root():
    return {"message": "ok"}


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
                "elapsed_seconds": round(elapsed, 2),
                "similar_cases_found": len(similar_cases),
            }
        }

    except Exception as e:
        elapsed = time.perf_counter() - started
        log_event("ASSESS_ERROR", f"error={repr(e)} elapsed={elapsed:.2f}s")

        raise HTTPException(
            status_code=500,
            detail=f"Failed to assess initiative: {str(e)}"
        )
    
@app.get("/assessments")
def list_assessments():
    assessments = load_assessments()

    summary = [
        {
            "id": item["id"],
            "initiative": item["initiative"],
            "created_at": item["created_at"],
            "viability_score": item.get("viability_score")
        }
        for item in assessments
    ]

    return {"data": summary}


@app.get("/assessments/{assessment_id}")
def get_assessment(assessment_id: str):
    assessments = load_assessments()

    for item in assessments:
        if item["id"] == assessment_id:
            return {"data": item}

    raise HTTPException(status_code=404, detail="Assessment não encontrado")

def print_assessment(result):
    print("\n=== AVALIAÇÃO DA INICIATIVA ===")
    print(f"\nProblema de negócio:\n{result.business_problem}")
    print(f"\nValor potencial:\n{result.potential_value}")
    print(f"\nComplexidade técnica:\n{result.technical_complexity}")

    print("\nPrincipais riscos:")
    for item in result.main_risks:
        print(f"- {item}")

    print("\nStack inicial sugerida:")
    for item in result.initial_stack:
        print(f"- {item}")

    print("\nQuick wins:")
    for item in result.quick_wins:
        print(f"- {item}")

    print(f"\nNota final de viabilidade: {result.viability_score}/10")


def main():
    print("Agente avaliador de iniciativas de IA")
    print("Digite a descrição da iniciativa e pressione ENTER.")
    print("Para encerrar, deixe vazio e pressione ENTER.\n")

    while True:
        user_input = input("Iniciativa: ").strip()

        if not user_input:
            print("Encerrando.")
            break

        try:
            result = assess_initiative(user_input)
            print_assessment(result)
        except Exception as e:
            print(f"\nErro ao avaliar iniciativa: {e}\n")


if __name__ == "__main__":
    main()