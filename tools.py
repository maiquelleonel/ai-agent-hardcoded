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
            "observability and audit logs"
        ],
        "contract_analysis": [
            "LLM provider",
            "document ingestion pipeline",
            "RAG over legal templates and policies",
            "human-in-the-loop review",
            "audit trail"
        ],
        "sales_ai": [
            "LLM provider",
            "CRM integration",
            "business rules layer",
            "analytics dashboard",
            "observability"
        ],
        "predictive_maintenance": [
            "time series data pipeline",
            "ML models for anomaly detection",
            "sensor/IoT integration",
            "alerting workflow",
            "operations dashboard"
        ],
        "knowledge_assistant": [
            "LLM provider",
            "document ingestion pipeline",
            "embeddings and vector store",
            "retrieval layer",
            "usage monitoring"
        ],
        "generic_ai_initiative": [
            "LLM provider",
            "application backend",
            "data access layer",
            "logging and monitoring",
            "security controls"
        ]
    }

    return stacks.get(initiative_type, stacks["generic_ai_initiative"])


def get_common_risks(initiative_type: str) -> list[str]:
    risks = {
        "internal_copilot": [
            "hallucination in employee-facing answers",
            "exposure of internal information",
            "weak integration with internal processes",
            "poor knowledge base quality"
        ],
        "contract_analysis": [
            "false negatives in risk detection",
            "legal overreliance without human review",
            "sensitive document exposure",
            "inconsistent clause interpretation"
        ],
        "sales_ai": [
            "biased prioritization",
            "poor CRM data quality",
            "low trust from sales teams",
            "weak explainability of recommendations"
        ],
        "predictive_maintenance": [
            "poor sensor data quality",
            "high false positive rate",
            "integration difficulty with operational systems",
            "long time to prove ROI"
        ],
        "knowledge_assistant": [
            "stale documents",
            "irrelevant retrieval",
            "hallucinated answers",
            "missing access control"
        ],
        "generic_ai_initiative": [
            "unclear business objective",
            "weak data foundation",
            "lack of governance",
            "underestimated integration complexity"
        ]
    }

    return risks.get(initiative_type, risks["generic_ai_initiative"])