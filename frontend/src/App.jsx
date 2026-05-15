import { useEffect, useState } from "react";
import "./App.css";
import "./styles.css";

const API_BASE = "http://127.0.0.1:8000";

function formatAssessment(saved) {
  if (!saved?.result) return "";

  const result = saved.result;
  const lines = [];

  lines.push("=== AVALIAÇÃO DA INICIATIVA ===");
  lines.push("");

  lines.push("Problema de negócio:");
  lines.push(result.business_problem || "");
  lines.push("");

  lines.push("Valor potencial:");
  lines.push(result.potential_value || "");
  lines.push("");

  lines.push("Complexidade técnica:");
  lines.push(result.technical_complexity || "");
  lines.push("");

  lines.push("Principais riscos:");
  (result.main_risks || []).forEach((item) => lines.push(`- ${item}`));
  lines.push("");

  lines.push("Stack inicial sugerida:");
  (result.initial_stack || []).forEach((item) => lines.push(`- ${item}`));
  lines.push("");

  lines.push("Quick wins:");
  (result.quick_wins || []).forEach((item) => lines.push(`- ${item}`));
  lines.push("");

  lines.push(`Nota final de viabilidade: ${result.viability_score ?? "-"} / 10`);

  if (result.scores) {
    lines.push("");
    lines.push("=== SCORES ===");
    lines.push(`Business value: ${result.scores.business_value}`);
    lines.push(`Technical feasibility: ${result.scores.technical_feasibility}`);
    lines.push(`Data readiness: ${result.scores.data_readiness}`);
    lines.push(`Governance risk: ${result.scores.governance_risk}`);
    lines.push(`Integration effort: ${result.scores.integration_effort}`);
    lines.push(`Time to value: ${result.scores.time_to_value}`);
    lines.push(`Overall viability: ${result.scores.overall_viability}`);
  }

  if (result.review_decision) {
    lines.push("");
    lines.push("=== REVIEW DECISION ===");
    lines.push(
      `Requires human review: ${
        result.review_decision.requires_human_review ? "yes" : "no"
      }`
    );
    lines.push(`Confidence: ${result.review_decision.confidence_level || ""}`);
    lines.push(`Reason: ${result.review_decision.review_reason || ""}`);
  }

  if (result.workflow_state) {
    lines.push("");
    lines.push("=== WORKFLOW STATE ===");
    Object.entries(result.workflow_state).forEach(([key, value]) => {
      lines.push(`${key}: ${String(value)}`);
    });
  }

  if (result.score_explanations?.length) {
    lines.push("");
    lines.push("=== SCORE EXPLANATIONS ===");
    result.score_explanations.forEach((item) => {
      lines.push(
        `- ${item.dimension}: ${item.original_score} -> ${item.adjusted_score} | ${item.reason}`
      );
    });
  }

  if (result.memory_context?.memory_summary) {
    lines.push("");
    lines.push("=== MEMORY SUMMARY ===");
    lines.push(result.memory_context.memory_summary);
  }

  if (result.document_context?.summary) {
    lines.push("");
    lines.push("=== DOCUMENT CONTEXT ===");
    lines.push(result.document_context.summary);
  }

  return lines.join("\n");
}

function formatComparison(data) {
  if (!data) return "";

  const lines = [];
  lines.push("=== COMPARAÇÃO ENTRE AVALIAÇÕES ===");
  lines.push("");
  lines.push("Resumo:");
  lines.push(data.summary || "");
  lines.push("");
  lines.push("Principais diferenças:");
  (data.major_differences || []).forEach((item) => lines.push(`- ${item}`));
  lines.push("");
  lines.push("Recomendação:");
  lines.push(data.recommendation || "");
  return lines.join("\n");
}

export default function App() {
  const [initiative, setInitiative] = useState("");
  const [file, setFile] = useState(null);

  const [responseText, setResponseText] = useState("");
  const [comparisonText, setComparisonText] = useState("");

  const [history, setHistory] = useState([]);
  const [selectedAssessment, setSelectedAssessment] = useState(null);

  const [compareCurrentId, setCompareCurrentId] = useState("");
  const [comparePreviousId, setComparePreviousId] = useState("");

  const [similarCases, setSimilarCases] = useState([]);
  const [memorySummary, setMemorySummary] = useState("");
  const [semanticSearchText, setSemanticSearchText] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("");
  const [showRawJson, setShowRawJson] = useState(false);

  useEffect(() => {
    loadHistory();
  }, []);

  async function loadHistory() {
    try {
      const res = await fetch(`${API_BASE}/assessments`);
      const payload = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(payload?.detail || `Erro HTTP: ${res.status}`);
      }

      setHistory(payload?.data || []);
    } catch (err) {
      setError(`Falha ao carregar histórico: ${err.message}`);
    }
  }

  function resetMessagesOnly() {
    setError("");
    setStatusMessage("");
  }

  function clearOutputs() {
    setResponseText("");
    setComparisonText("");
    setSelectedAssessment(null);
    setSimilarCases([]);
    setMemorySummary("");
    setShowRawJson(false);
  }

  function handleCloseAssessment() {
    setSelectedAssessment(null);
    setResponseText("");
    setSimilarCases([]);
    setMemorySummary("");
    setShowRawJson(false);
    setStatusMessage("Painel de resultado fechado.");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    resetMessagesOnly();
    clearOutputs();

    if (!initiative.trim()) {
      setError("Digite uma iniciativa para analisar.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/assess`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          initiative: initiative.trim()
        })
      });

      const payload = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(payload?.detail || "Falha ao consultar o backend.");
      }

      const data = payload?.data;
      if (!data) {
        throw new Error("Resposta do backend sem campo data.");
      }

      setSelectedAssessment(data);
      setResponseText(formatAssessment(data));
      setSimilarCases(data.result?.memory_context?.similar_cases || []);
      setMemorySummary(data.result?.memory_context?.memory_summary || "");
      setShowRawJson(false);
      setStatusMessage("Iniciativa analisada com sucesso.");
      await loadHistory();
    } catch (err) {
      setError(`Falha ao analisar iniciativa: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleFileSubmit(e) {
    e.preventDefault();
    resetMessagesOnly();
    clearOutputs();

    if (!file) {
      setError("Selecione um arquivo .txt ou .md.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/assess-file`, {
        method: "POST",
        body: formData
      });

      const payload = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(payload?.detail || "Falha ao consultar o backend.");
      }

      const data = payload?.data;
      if (!data) {
        throw new Error("Resposta do backend sem campo data.");
      }

      setSelectedAssessment(data);
      setResponseText(formatAssessment(data));
      setSimilarCases(data.result?.memory_context?.similar_cases || []);
      setMemorySummary(data.result?.memory_context?.memory_summary || "");
      setShowRawJson(false);
      setStatusMessage("Arquivo analisado com sucesso.");
      await loadHistory();
    } catch (err) {
      setError(`Falha ao analisar arquivo: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function openAssessment(id) {
    resetMessagesOnly();
    setComparisonText("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/assessments/${id}`);
      const payload = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(payload?.detail || "Falha ao carregar assessment.");
      }

      const data = payload?.data;
      if (!data) {
        throw new Error("Resposta do backend sem campo data.");
      }

      setSelectedAssessment(data);
      setResponseText(formatAssessment(data));
      setSimilarCases(data.result?.memory_context?.similar_cases || []);
      setMemorySummary(data.result?.memory_context?.memory_summary || "");
      setShowRawJson(false);
      setStatusMessage(`Assessment ${id} carregado com sucesso.`);
    } catch (err) {
      setError(`Falha ao abrir assessment: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleCompare() {
    resetMessagesOnly();
    setComparisonText("");

    if (!compareCurrentId || !comparePreviousId) {
      setError("Selecione dois assessments para comparar.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/compare`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          current_id: compareCurrentId,
          previous_id: comparePreviousId
        })
      });

      const payload = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(payload?.detail || "Falha ao comparar assessments.");
      }

      const data = payload?.data;
      setComparisonText(formatComparison(data));
      setStatusMessage("Comparação executada com sucesso.");
    } catch (err) {
      setError(`Falha ao comparar assessments: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  async function handleSemanticSearch() {
    resetMessagesOnly();

    const textToSearch = semanticSearchText.trim() || initiative.trim();

    if (!textToSearch) {
      setError("Digite uma iniciativa para buscar casos semelhantes.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/memory/search-semantic`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          initiative: textToSearch
        })
      });

      const payload = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(payload?.detail || `Erro HTTP: ${res.status}`);
      }

      const data = payload?.data || {};
      setSimilarCases(data.similar_cases || []);
      setMemorySummary(data.memory_summary || "");
      setStatusMessage("Busca semântica executada com sucesso.");
    } catch (err) {
      setError(`Falha ao buscar memória semântica: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app-shell dashboard-shell">
      <div className="container dashboard-container">
        <h1>AI Initiative Assessment Agent</h1>

        <div className="dashboard-grid">
          <div className="dashboard-left">
            <div className="card compact-card">
              <h2>Analisar iniciativa por texto</h2>
              <form onSubmit={handleSubmit}>
                <label htmlFor="initiative" className="label">
                  Descrição da iniciativa
                </label>
                <textarea
                  id="initiative"
                  className="textarea"
                  value={initiative}
                  onChange={(e) => setInitiative(e.target.value)}
                  placeholder="Descreva a iniciativa de IA..."
                  rows={6}
                />
                <button type="submit" className="primary-button" disabled={loading}>
                  {loading ? "Processando..." : "Analisar iniciativa"}
                </button>
              </form>
            </div>

            <div className="card compact-card">
              <h2>Analisar iniciativa por arquivo</h2>
              <form onSubmit={handleFileSubmit}>
                <input
                  type="file"
                  accept=".txt,.md"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                <button type="submit" className="primary-button" disabled={loading}>
                  {loading ? "Processando..." : "Enviar arquivo"}
                </button>
              </form>
            </div>

            <div className="card compact-card">
              <h2>Busca semântica de casos semelhantes</h2>

              <label htmlFor="semanticSearch" className="label">
                Texto para busca semântica
              </label>
              <textarea
                id="semanticSearch"
                className="textarea"
                value={semanticSearchText}
                onChange={(e) => setSemanticSearchText(e.target.value)}
                placeholder="Opcional: digite um texto para buscar casos parecidos semanticamente..."
                rows={4}
              />

              <button
                type="button"
                className="secondary-button"
                onClick={handleSemanticSearch}
                disabled={loading}
              >
                {loading ? "Processando..." : "Buscar casos semelhantes"}
              </button>

              <label className="label response-label">Resumo da memória</label>
              <textarea
                className="textarea response-box memory-summary-box"
                value={memorySummary}
                readOnly
                placeholder="O resumo da memória aparecerá aqui..."
                rows={4}
              />
            </div>

            <div className="card compact-card">
              <h2>Comparar avaliações</h2>

              <div className="compare-grid">
                <div>
                  <label className="label">Assessment atual</label>
                  <select
                    className="select"
                    value={compareCurrentId}
                    onChange={(e) => setCompareCurrentId(e.target.value)}
                  >
                    <option value="">Selecione</option>
                    {history.map((item) => (
                      <option key={`current-${item.id}`} value={item.id}>
                        {item.id}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="label">Assessment anterior</label>
                  <select
                    className="select"
                    value={comparePreviousId}
                    onChange={(e) => setComparePreviousId(e.target.value)}
                  >
                    <option value="">Selecione</option>
                    {history.map((item) => (
                      <option key={`previous-${item.id}`} value={item.id}>
                        {item.id}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                type="button"
                className="primary-button"
                onClick={handleCompare}
                disabled={loading}
              >
                {loading ? "Processando..." : "Comparar"}
              </button>
            </div>

            <div className="card compact-card scroll-card">
              <h2>Histórico de avaliações</h2>

              {history.length === 0 ? (
                <p>Nenhuma avaliação encontrada.</p>
              ) : (
                <div className="history-list">
                  {history.map((item) => (
                    <div key={item.id} className="history-item">
                      <div className="history-main">
                        <div className="history-id">{item.id}</div>
                        <div className="history-date">{item.created_at}</div>
                        <div className="history-score">
                          Viability score: {item.viability_score}/10
                        </div>
                        <div className="history-snippet">
                          {(item.initiative || "").slice(0, 120)}
                          {(item.initiative || "").length > 120 ? "..." : ""}
                        </div>
                      </div>

                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => openAssessment(item.id)}
                      >
                        Abrir
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="dashboard-right">
            {statusMessage && <div className="status success">{statusMessage}</div>}
            {error && <div className="status error">{error}</div>}

            <div className="card result-card">
              <div className="result-header">
                <h2>Resultado da avaliação</h2>

                <div className="result-actions">
                  {selectedAssessment && (
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={() => setShowRawJson((prev) => !prev)}
                    >
                      {showRawJson ? "Ocultar JSON" : "Ver JSON"}
                    </button>
                  )}

                  {selectedAssessment && (
                    <button
                      type="button"
                      className="secondary-button"
                      onClick={handleCloseAssessment}
                    >
                      Fechar
                    </button>
                  )}
                </div>
              </div>

              <textarea
                className="textarea response-box result-main-box"
                value={responseText}
                readOnly
                placeholder="O resultado aparecerá aqui..."
                rows={22}
              />
            </div>

            {selectedAssessment && showRawJson && (
              <div className="card compact-card raw-json-card">
                <h2>Assessment carregado</h2>
                <pre className="json-box">
                  {JSON.stringify(selectedAssessment, null, 2)}
                </pre>
              </div>
            )}

            <div className="card compact-card scroll-card">
              <h2>Casos semelhantes</h2>

              {similarCases.length === 0 ? (
                <p>Nenhum caso semelhante encontrado.</p>
              ) : (
                <div className="similar-cases-list">
                  {similarCases.map((item) => (
                    <div key={item.assessment_id} className="similar-case-card">
                      <div>
                        <strong>ID:</strong> {item.assessment_id}
                      </div>
                      <div>
                        <strong>Score:</strong> {item.viability_score}/10
                      </div>
                      <div>
                        <strong>Similaridade:</strong> {item.similarity_score}%
                      </div>
                      {item.review_status && (
                        <div>
                          <strong>Review:</strong> {item.review_status}
                        </div>
                      )}
                      {item.review_reason && (
                        <div>
                          <strong>Motivo:</strong> {item.review_reason}
                        </div>
                      )}
                      <div className="similar-snippet">{item.initiative_excerpt}</div>
                      <button
                        type="button"
                        className="link-button"
                        onClick={() => openAssessment(item.assessment_id)}
                      >
                        Abrir assessment
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="card compact-card">
              <h2>Resultado da comparação</h2>
              <textarea
                className="textarea response-box comparison-box"
                value={comparisonText}
                readOnly
                placeholder="A comparação aparecerá aqui..."
                rows={10}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}