import json
from typing import Any, Dict

from prompts import SYSTEM_PROMPT
from schemas import (
    AssessmentComparisonResult,
    AssessmentScores,
    InitiativeAssessment,
    MemoryContext,
    ParsedInitiative,
    ReviewDecision,
    ScoreExplanation,
    SimilarCase,
)
from services.factory import get_ai_service
from utils import (
    detect_initiative_type,
    get_common_risks,
    get_recommended_stack,
)

# Inicializa o serviço de IA configurado via ENV
ai_service = get_ai_service()

TOOLS = [
    {
        "type": "function",
        "name": "detect_initiative_type",
        "description": "Classifica o tipo principal da iniciativa de IA.",
        "parameters": {
            "type": "object",
            "properties": {"description": {"type": "string", "description": "Descrição textual da iniciativa"}},
            "required": ["description"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_recommended_stack",
        "description": "Retorna uma stack inicial recomendada para um tipo de iniciativa.",
        "parameters": {
            "type": "object",
            "properties": {"initiative_type": {"type": "string", "description": "Tipo classificado da iniciativa"}},
            "required": ["initiative_type"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "get_common_risks",
        "description": "Retorna riscos comuns para um tipo de iniciativa.",
        "parameters": {
            "type": "object",
            "properties": {"initiative_type": {"type": "string", "description": "Tipo classificado da iniciativa"}},
            "required": ["initiative_type"],
            "additionalProperties": False,
        },
    },
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
    list_fields = ["target_users", "required_data", "integrations", "constraints", "regulatory_risks"]
    for field in list_fields:
        if isinstance(data.get(field), str):
            data[field] = [data[field]]
    return data


def parse_initiative_description(initiative_description: str) -> ParsedInitiative:
    content = ai_service.generate_response(
        messages=[
            {"role": "system", "content": "Responda apenas em JSON válido."},
            {
                "role": "user",
                "content": f"Leia a iniciativa abaixo e extraia uma estrutura padronizada:\n\n{initiative_description}",
            },
        ],
        response_format={"type": "json_object"},
    )
    data = json.loads(content)
    data = normalize_parsed_initiative(data)
    return ParsedInitiative.model_validate(data)


def run_tool_phase(initiative_description: str, memory_summary: str = ""):
    # Nota: A Service Layer precisa ser adaptada para suportar tool calls explicitamente
    # se quisermos ser 100% agnósticos. Por enquanto, a OpenAIService suporta tool_calls.
    return ai_service.client.chat.completions.create(
        model=ai_service.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Analise a iniciativa: {initiative_description}\n\nContexto Histórico: {memory_summary}",
            },
        ],
        tools=TOOLS,
    )


def run_final_phase(initiative_description: str, tool_context: dict, retry_count: int = 0) -> InitiativeAssessment:
    content = ai_service.generate_response(
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Analise a iniciativa: {initiative_description}\n\nContexto: {json.dumps(tool_context)}",
            },
        ],
        response_format={"type": "json_object"},
    )
    data = json.loads(content)
    data = normalize_response(data)
    assessment = InitiativeAssessment.model_validate(data)
    if not 0 <= assessment.viability_score <= 10:
        raise ValueError("viability_score fora do intervalo (0-10).")
    return assessment


def compute_overall_viability(scores: AssessmentScores) -> int:
    weighted = (
        scores.business_value * 0.25
        + scores.technical_feasibility * 0.20
        + scores.data_readiness * 0.15
        + (10 - scores.governance_risk) * 0.15
        + (10 - scores.integration_effort) * 0.10
        + scores.time_to_value * 0.15
    )
    return round(weighted)


def score_initiative(parsed: ParsedInitiative, tool_context: dict) -> AssessmentScores:
    content = ai_service.generate_response(
        messages=[
            {"role": "system", "content": "Responda apenas em JSON válido."},
            {
                "role": "user",
                "content": f"Avalie a iniciativa: {parsed.model_dump_json()} | Contexto: {json.dumps(tool_context)}",
            },
        ],
        response_format={"type": "json_object"},
    )
    data = json.loads(content)
    scores = AssessmentScores.model_validate(data)
    scores.overall_viability = compute_overall_viability(scores)
    return scores


def apply_deterministic_rules(
    parsed: ParsedInitiative, scores: AssessmentScores
) -> tuple[AssessmentScores, list[ScoreExplanation]]:
    explanations: list[ScoreExplanation] = []

    def adjust(field_name: str, delta: int, reason: str):
        original = getattr(scores, field_name)
        adjusted = max(0, min(10, original + delta))
        if adjusted != original:
            setattr(scores, field_name, adjusted)
            explanations.append(
                ScoreExplanation(dimension=field_name, original_score=original, adjusted_score=adjusted, reason=reason)
            )

    text_blob = " ".join([parsed.business_problem, parsed.expected_value, parsed.summary]).lower()
    if any(term in text_blob for term in ["lgpd", "gdpr", "dados pessoais"]):
        adjust("governance_risk", +2, "A iniciativa menciona dados pessoais ou regulação de privacidade.")

    scores.overall_viability = compute_overall_viability(scores)
    return scores, explanations


def decide_human_review(parsed: ParsedInitiative, scores: AssessmentScores) -> ReviewDecision:
    reasons = []
    if scores.governance_risk >= 8:
        reasons.append("High governance risk")
    if scores.integration_effort >= 8:
        reasons.append("High integration effort")
    if reasons:
        return ReviewDecision(requires_human_review=True, confidence_level="medium", review_reason="; ".join(reasons))
    return ReviewDecision(requires_human_review=False, confidence_level="high", review_reason="No critical flags")


def assess_initiative(
    initiative_description: str, similar_cases: list[dict] | None = None, memory_summary: str = ""
) -> InitiativeAssessment:
    if similar_cases is None:
        similar_cases = []
    parsed = parse_initiative_description(initiative_description)
    _ = run_tool_phase(initiative_description, memory_summary)

    # Execução das tools (simulada)
    tool_context = {"parsed_initiative": parsed.model_dump()}

    scores = score_initiative(parsed, tool_context)
    scores, score_explanations = apply_deterministic_rules(parsed, scores)
    review_decision = decide_human_review(parsed, scores)

    assessment = run_final_phase(initiative_description, tool_context)
    assessment.viability_score = scores.overall_viability
    assessment.scores = scores
    assessment.score_explanations = score_explanations
    assessment.review_decision = review_decision
    assessment.memory_context = MemoryContext(
        similar_cases=[SimilarCase.model_validate(case) for case in similar_cases],
        memory_summary=memory_summary,
    )
    return assessment


def compare_assessments(current_assessment: dict, previous_assessment: dict) -> AssessmentComparisonResult:
    content = ai_service.generate_response(
        messages=[
            {"role": "system", "content": "Responda apenas em JSON válido."},
            {
                "role": "user",
                "content": f"Compare:\n{json.dumps(current_assessment)}\n\nE:\n{json.dumps(previous_assessment)}",
            },
        ],
        response_format={"type": "json_object"},
    )
    data = json.loads(content)
    return AssessmentComparisonResult.model_validate(data)
