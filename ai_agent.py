import os
import json
import math
from typing import Any, Dict

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from prompts import SYSTEM_PROMPT
from schemas import (
    InitiativeAssessment,
    AssessmentComparisonResult,
    ParsedInitiative,
    AssessmentScores,
    WorkflowState,
    ScoreExplanation,
    ReviewDecision,
    MemoryContext,
    SimilarCase,
)
from tools import detect_initiative_type, get_recommended_stack, get_common_risks

load_dotenv()

MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-5")
client = OpenAI()

TOOLS = [
    {
        "type": "function",
        "name": "detect_initiative_type",
        "description": "Classifica o tipo principal da iniciativa de IA.",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Descrição textual da iniciativa"
                }
            },
            "required": ["description"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_recommended_stack",
        "description": "Retorna uma stack inicial recomendada para um tipo de iniciativa.",
        "parameters": {
            "type": "object",
            "properties": {
                "initiative_type": {
                    "type": "string",
                    "description": "Tipo classificado da iniciativa"
                }
            },
            "required": ["initiative_type"],
            "additionalProperties": False
        }
    },
    {
        "type": "function",
        "name": "get_common_risks",
        "description": "Retorna riscos comuns para um tipo de iniciativa.",
        "parameters": {
            "type": "object",
            "properties": {
                "initiative_type": {
                    "type": "string",
                    "description": "Tipo classificado da iniciativa"
                }
            },
            "required": ["initiative_type"],
            "additionalProperties": False
        }
    }
]


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    if tool_name == "detect_initiative_type":
        return detect_initiative_type(arguments["description"])

    if tool_name == "get_recommended_stack":
        return get_recommended_stack(arguments["initiative_type"])

    if tool_name == "get_common_risks":
        return get_common_risks(arguments["initiative_type"])

    raise ValueError(f"Tool desconhecida: {tool_name}")


def normalize_response(data: dict) -> dict:
    if isinstance(data.get("potential_value"), list):
        data["potential_value"] = " ".join(str(item) for item in data["potential_value"])

    if isinstance(data.get("initial_stack"), dict):
        flattened = []
        for key, value in data["initial_stack"].items():
            if isinstance(value, list):
                flattened.extend(str(item) for item in value)
            else:
                flattened.append(f"{key}: {value}")
        data["initial_stack"] = flattened

    if isinstance(data.get("main_risks"), str):
        data["main_risks"] = [data["main_risks"]]

    if isinstance(data.get("quick_wins"), str):
        data["quick_wins"] = [data["quick_wins"]]

    return data


def normalize_parsed_initiative(data: dict) -> dict:
    list_fields = [
        "target_users",
        "required_data",
        "integrations",
        "constraints",
        "regulatory_risks",
    ]

    for field in list_fields:
        if isinstance(data.get(field), str):
            data[field] = [data[field]]

    return data


def extract_tool_calls(response) -> list[dict]:
    tool_calls = []

    for item in response.output:
        if item.type == "function_call":
            tool_calls.append({
                "call_id": item.call_id,
                "name": item.name,
                "arguments": json.loads(item.arguments)
            })

    return tool_calls


def parse_initiative_description(initiative_description: str) -> ParsedInitiative:
    response = client.responses.create(
        model=MODEL_NAME,
        instructions="""
Você é um arquiteto sênior de soluções de IA para ambiente enterprise.

Sua tarefa é ler uma descrição de iniciativa de IA e convertê-la em uma estrutura objetiva e consistente.

Regras:
- Seja conservador quando houver ambiguidade.
- Faça inferências razoáveis, mas não invente detalhes específicos demais.
- Responda apenas em JSON válido.
- Não inclua campos extras.
""".strip(),
        input=f"""
Leia a iniciativa abaixo e extraia uma estrutura padronizada.

INICIATIVA:
{initiative_description}

Responda obrigatoriamente em JSON com esta estrutura:

{{
  "initiative_name": "texto",
  "business_area": "texto",
  "business_problem": "texto",
  "target_users": ["item 1", "item 2"],
  "initiative_type": "texto",
  "expected_value": "texto",
  "required_data": ["item 1", "item 2"],
  "integrations": ["item 1", "item 2"],
  "constraints": ["item 1", "item 2"],
  "regulatory_risks": ["item 1", "item 2"],
  "summary": "texto"
}}

Regras obrigatórias:
- Todos os campos devem existir
- Campos de lista devem ser listas de strings
- Campos textuais devem ser string
- Não inclua explicações fora do JSON
""".strip(),
        text={"format": {"type": "json_object"}}
    )

    raw_text = response.output_text
    data = json.loads(raw_text)
    data = normalize_parsed_initiative(data)

    return ParsedInitiative.model_validate(data)


def run_tool_phase(initiative_description: str, memory_summary: str = ""):
    response = client.responses.create(
        model=MODEL_NAME,
        instructions=SYSTEM_PROMPT,
        input=f"""
Analise a iniciativa abaixo e use as tools disponíveis quando necessário para enriquecer a avaliação final.

Iniciativa:
{initiative_description}

CONTEXTO HISTÓRICO:
{memory_summary or "Nenhum caso semelhante disponível."}

Antes de responder, descubra:
1. o tipo da iniciativa
2. a stack recomendada
3. os riscos comuns

Não entregue a resposta final ainda. Apenas chame as tools necessárias.
- Considere histórico de casos semelhantes quando disponível, mas não copie cegamente conclusões anteriores
- Use o contexto histórico para aumentar consistência, não para substituir julgamento técnico
""".strip(),
        tools=TOOLS
    )

    return response


def run_final_phase(
    initiative_description: str,
    tool_context: dict,
    retry_count: int = 0
) -> InitiativeAssessment:
    retry_note = ""
    if retry_count > 0:
        retry_note = """
Sua resposta anterior violou o schema esperado.
Corrija e responda estritamente no formato solicitado.
""".strip()

    response = client.responses.create(
        model=MODEL_NAME,
        instructions=SYSTEM_PROMPT,
        input=f"""
Analise a seguinte iniciativa de IA em contexto enterprise:

DESCRIÇÃO:
{initiative_description}

CONTEXTO ENRIQUECIDO POR TOOLS:
{json.dumps(tool_context, ensure_ascii=False, indent=2)}

{retry_note}

Responda obrigatoriamente em JSON VÁLIDO, sem texto antes ou depois.

Use EXATAMENTE esta estrutura:

{{
  "business_problem": "texto",
  "potential_value": "texto",
  "technical_complexity": "texto",
  "main_risks": ["item 1", "item 2", "item 3"],
  "initial_stack": ["item 1", "item 2", "item 3"],
  "quick_wins": ["item 1", "item 2", "item 3"],
  "viability_score": 8
}}

Regras obrigatórias:
- business_problem deve ser string
- potential_value deve ser string
- technical_complexity deve ser string
- main_risks deve ser lista de strings
- initial_stack deve ser lista de strings
- quick_wins deve ser lista de strings
- viability_score deve ser inteiro entre 0 e 10
- Não inclua campos extras
- Seja conservador quando houver ambiguidade
- Considere os scores, explicações e decisão de revisão humana presentes no contexto enriquecido
- viability_score deve ser coerente com overall_viability
- Considere histórico de casos semelhantes quando disponível, mas não copie cegamente conclusões anteriores
- Use o contexto histórico para aumentar consistência, não para substituir julgamento técnico
""".strip(),
        text={"format": {"type": "json_object"}}
    )

    raw_text = response.output_text
    data = json.loads(raw_text)
    data = normalize_response(data)

    assessment = InitiativeAssessment.model_validate(data)

    if not 0 <= assessment.viability_score <= 10:
        raise ValueError("viability_score fora do intervalo esperado (0-10).")

    return assessment


def get_embedding(text: str) -> list[float]:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
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


def compute_overall_viability(scores: AssessmentScores) -> int:
    weighted = (
        scores.business_value * 0.25 +
        scores.technical_feasibility * 0.20 +
        scores.data_readiness * 0.15 +
        (10 - scores.governance_risk) * 0.15 +
        (10 - scores.integration_effort) * 0.10 +
        scores.time_to_value * 0.15
    )
    return round(weighted)


def score_initiative(
    parsed: ParsedInitiative,
    tool_context: dict
) -> AssessmentScores:
    response = client.responses.create(
        model=MODEL_NAME,
        instructions="""
Você é um arquiteto sênior de IA enterprise.

Sua tarefa é atribuir subscores objetivos a uma iniciativa de IA.

Regras:
- Seja conservador.
- Use escala de 0 a 10.
- governance_risk: 0 significa risco muito baixo, 10 muito alto.
- integration_effort: 0 significa esforço muito baixo, 10 muito alto.
- Responda apenas em JSON válido.
- Não inclua campos extras.
""".strip(),
        input=f"""
Avalie a iniciativa abaixo e atribua scores.

PARSED_INITIATIVE:
{json.dumps(parsed.model_dump(), ensure_ascii=False, indent=2)}

TOOL_CONTEXT:
{json.dumps(tool_context, ensure_ascii=False, indent=2)}

Responda em JSON com esta estrutura:

{{
  "business_value": 0,
  "technical_feasibility": 0,
  "data_readiness": 0,
  "governance_risk": 0,
  "integration_effort": 0,
  "time_to_value": 0,
  "overall_viability": 0
}}

Regras:
- Todos os campos devem ser inteiros entre 0 e 10
- overall_viability pode ser provisório
- Não inclua explicações fora do JSON
""".strip(),
        text={"format": {"type": "json_object"}}
    )

    raw_text = response.output_text
    data = json.loads(raw_text)

    scores = AssessmentScores.model_validate(data)
    scores.overall_viability = compute_overall_viability(scores)
    return scores


def clamp_score(value: int) -> int:
    return max(0, min(10, value))


def apply_deterministic_rules(
    parsed: ParsedInitiative,
    scores: AssessmentScores
) -> tuple[AssessmentScores, list[ScoreExplanation]]:
    explanations: list[ScoreExplanation] = []

    def adjust(field_name: str, delta: int, reason: str):
        original = getattr(scores, field_name)
        adjusted = clamp_score(original + delta)

        if adjusted != original:
            setattr(scores, field_name, adjusted)
            explanations.append(
                ScoreExplanation(
                    dimension=field_name,
                    original_score=original,
                    adjusted_score=adjusted,
                    reason=reason
                )
            )

    text_blob = " ".join([
        parsed.business_problem,
        parsed.expected_value,
        parsed.summary,
        " ".join(parsed.constraints),
        " ".join(parsed.regulatory_risks),
        " ".join(parsed.integrations),
        parsed.initiative_type,
    ]).lower()

    if any(term in text_blob for term in ["lgpd", "gdpr", "dados pessoais", "dados sensíveis", "dados sensiveis"]):
        adjust(
            "governance_risk",
            +2,
            "A iniciativa menciona dados pessoais ou regulação de privacidade."
        )

    if any(term in text_blob for term in ["erp", "crm", "legado", "sistema legado", "múltiplos sistemas", "multiplos sistemas"]):
        adjust(
            "integration_effort",
            +2,
            "A iniciativa sugere integração com sistemas corporativos ou legados."
        )

    if any(term in text_blob for term in ["piloto", "poc", "prova de conceito", "mvp"]):
        adjust(
            "time_to_value",
            +1,
            "A iniciativa parece ter caminho de adoção incremental via piloto ou PoC."
        )

    if any(term in text_blob for term in ["sem dados", "dados insuficientes", "baixa qualidade de dados"]):
        adjust(
            "data_readiness",
            -2,
            "A descrição sugere baixa prontidão ou qualidade de dados."
        )

    if any(term in text_blob for term in ["decisão automática", "decisao automatica", "compliance", "jurídico", "juridico", "fraude", "crédito", "credito"]):
        adjust(
            "governance_risk",
            +1,
            "A iniciativa atua em domínio sensível ou regulado."
        )

    scores.overall_viability = compute_overall_viability(scores)
    return scores, explanations


def decide_human_review(
    parsed: ParsedInitiative,
    scores: AssessmentScores
) -> ReviewDecision:
    reasons = []

    if scores.governance_risk >= 8:
        reasons.append("High governance risk")

    if scores.integration_effort >= 8:
        reasons.append("High integration effort")

    if scores.data_readiness <= 3:
        reasons.append("Low data readiness")

    if parsed.initiative_type in ["contract_analysis", "predictive_maintenance"]:
        reasons.append("Sensitive initiative type")

    if reasons:
        confidence = "medium"
        if len(reasons) >= 3:
            confidence = "low"

        return ReviewDecision(
            requires_human_review=True,
            confidence_level=confidence,
            review_reason="; ".join(reasons)
        )

    return ReviewDecision(
        requires_human_review=False,
        confidence_level="high",
        review_reason="No critical review flags detected"
    )


def assess_initiative(
    initiative_description: str,
    similar_cases: list[dict] | None = None,
    memory_summary: str = ""
) -> InitiativeAssessment:
    if similar_cases is None:
        similar_cases = []

    print("\n[LOG] Iniciando avaliação da iniciativa")

    workflow = WorkflowState(received=True)

    print("[LOG] Executando parse estruturado da iniciativa...")
    parsed = parse_initiative_description(initiative_description)
    workflow.parsed = True
    print(f"[LOG] Parse concluído | initiative_type={parsed.initiative_type}")

    enriched_description = f"""
Resumo estruturado da iniciativa:

Nome da iniciativa: {parsed.initiative_name}
Área de negócio: {parsed.business_area}
Problema de negócio: {parsed.business_problem}
Usuários impactados: {", ".join(parsed.target_users)}
Tipo da iniciativa: {parsed.initiative_type}
Valor esperado: {parsed.expected_value}
Dados necessários: {", ".join(parsed.required_data)}
Integrações: {", ".join(parsed.integrations)}
Restrições: {", ".join(parsed.constraints)}
Riscos regulatórios: {", ".join(parsed.regulatory_risks)}
Resumo executivo: {parsed.summary}

Descrição original:
{initiative_description}
""".strip()

    print("[LOG] Executando fase de tool calling...")
    tool_response = run_tool_phase(enriched_description, memory_summary=memory_summary)
    tool_calls = extract_tool_calls(tool_response)

    tool_context = {
        "parsed_initiative": parsed.model_dump(),
        "memory_context": {
            "similar_cases": similar_cases,
            "memory_summary": memory_summary,
        }
    }

    for call in tool_calls:
        result = execute_tool(call["name"], call["arguments"])
        tool_context[call["name"]] = result
        print(f"[LOG] Tool chamada: {call['name']} | argumentos={call['arguments']} | resultado={result}")

    if "detect_initiative_type" not in tool_context:
        detected = detect_initiative_type(enriched_description)
        tool_context["detect_initiative_type"] = detected
        print(f"[LOG] Fallback detect_initiative_type={detected}")

    workflow.classified = True

    initiative_type = tool_context["detect_initiative_type"]

    if "get_recommended_stack" not in tool_context:
        stack = get_recommended_stack(initiative_type)
        tool_context["get_recommended_stack"] = stack
        print(f"[LOG] Fallback get_recommended_stack={stack}")
    workflow.stack_enriched = True

    if "get_common_risks" not in tool_context:
        risks = get_common_risks(initiative_type)
        tool_context["get_common_risks"] = risks
        print(f"[LOG] Fallback get_common_risks={risks}")
    workflow.risks_enriched = True

    print("[LOG] Calculando subscores...")
    scores = score_initiative(parsed, tool_context)
    workflow.scored = True
    print(f"[LOG] Score calculado | overall_viability={scores.overall_viability}")

    print("[LOG] Aplicando regras determinísticas...")
    scores, score_explanations = apply_deterministic_rules(parsed, scores)
    workflow.rules_applied = True
    print(f"[LOG] Score ajustado | overall_viability={scores.overall_viability}")

    print("[LOG] Decidindo revisão humana...")
    review_decision = decide_human_review(parsed, scores)
    workflow.review_decided = True
    print(f"[LOG] Human review={review_decision.requires_human_review} | confidence={review_decision.confidence_level}")

    max_retries = 2

    for attempt in range(max_retries + 1):
        try:
            print(f"[LOG] Gerando resposta final | tentativa={attempt + 1}")
            assessment = run_final_phase(
                initiative_description=enriched_description,
                tool_context={
                    **tool_context,
                    "scores": scores.model_dump(),
                    "score_explanations": [item.model_dump() for item in score_explanations],
                    "review_decision": review_decision.model_dump(),
                },
                retry_count=attempt
            )

            assessment.viability_score = scores.overall_viability
            assessment.scores = scores
            assessment.score_explanations = score_explanations
            assessment.review_decision = review_decision
            assessment.memory_context = MemoryContext(
                similar_cases=[SimilarCase.model_validate(case) for case in similar_cases],
                memory_summary=memory_summary
            )
            workflow.completed = True
            assessment.workflow_state = workflow

            print("[LOG] Resposta validada com sucesso")
            return assessment

        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            print(f"[LOG] Falha de validação/parsing: {e}")
            if attempt == max_retries:
                new_func(max_retries, e)

    raise RuntimeError("Fluxo inesperado no agente.")

def new_func(max_retries, e):
    raise ValueError(f"Falha após {max_retries + 1} tentativas: {e}") from e


def compare_assessments(current_assessment: dict, previous_assessment: dict) -> AssessmentComparisonResult:
    response = client.responses.create(
        model=MODEL_NAME,
        instructions="""
Você é um arquiteto sênior de soluções de IA para ambiente enterprise.

Sua tarefa é comparar duas análises de iniciativas de IA e produzir um resumo executivo e técnico.

Regras:
- Seja objetivo, claro e profissional.
- Destaque diferenças realmente relevantes.
- Considere principalmente: score, problema de negócio, valor potencial, complexidade, riscos, stack e quick wins.
- A resposta deve ser em JSON válido, sem texto extra.
""".strip(),
        input=f"""
Compare as duas análises abaixo.

ANÁLISE ATUAL:
{json.dumps(current_assessment, ensure_ascii=False, indent=2)}

ANÁLISE ANTERIOR:
{json.dumps(previous_assessment, ensure_ascii=False, indent=2)}

Responda obrigatoriamente em JSON com esta estrutura:

{{
  "summary": "texto",
  "major_differences": ["diferença 1", "diferença 2", "diferença 3"],
  "recommendation": "texto"
}}

Regras obrigatórias:
- summary deve ser string
- major_differences deve ser lista de strings
- recommendation deve ser string
- não inclua campos extras
""".strip(),
        text={"format": {"type": "json_object"}}
    )

    raw_text = response.output_text
    data = json.loads(raw_text)

    return AssessmentComparisonResult.model_validate(data)