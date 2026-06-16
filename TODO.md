# Planejamento do Projeto — AI Agent Hardcoded

## 🚀 Próximos Passos (Backlog)

### Refatoração para Arquitetura Orientada a Objetos (OO)
- [ ] **Extração de Repositórios**: Criar classes em `repositories/` para encapsular a lógica de persistência (JSON), removendo dependências de `Path` e `json` dos utilitários.
- [ ] **Modelos de Domínio**: Criar classes em `models/` para representar `Initiative` e `Assessment`, encapsulando métodos de validação e cálculo.
- [ ] **Engines do Agente**: Migrar a lógica de `ai_agent.py` para classes que herdem de uma base `BaseAgent`.
- [ ] Ajuste final de infraestrutura (commit assinado)

### Melhorias na Service Layer
- [ ] **Suporte a Tools (Gemini)**: Implementar tool calling para o Gemini usando a nova sintaxe de `types.Tool`.
- [ ] **Cache de Embeddings**: Adicionar uma camada de cache para embeddings (evitar chamadas repetidas para iniciativas iguais).

### Observabilidade
- [ ] **Logs Estruturados**: Trocar `print` por um logger profissional (como `loguru`).
