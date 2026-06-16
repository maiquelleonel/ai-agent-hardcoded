# 🤖 AI Agents Harness & Architecture

Este arquivo documenta as regras de arquitetura e convenções de desenvolvimento para este projeto.

## 1. Princípios de Arquitetura

### Service Layer (Isolamento Total)
- **Regra de Ouro**: Nenhuma implementação de serviço (`OpenAIService`, `GeminiService`, etc.) deve importar ou depender da outra.
- **Independência**: Cada serviço deve ser uma implementação autônoma da interface `BaseAIService`.
- **Injeção**: A lógica de orquestração deve sempre passar pelo `factory.get_ai_service()`.

### Modularização
- **`utils.py`**: Apenas funções puramente utilitárias (sem lógica de negócio pesada, sem dependências circulares).
- **`services/`**: Camada exclusiva de integração com provedores de IA.
- **`dtos.py`**: Definição de objetos de transporte de dados (Request Models).
- **`schemas.py`**: Definição de modelos de dados de domínio (Pydantic).

## 2. Padrões de Desenvolvimento

### Respeito ao Código Existente
- **Foco Cirúrgico**: Quando ajustes específicos forem solicitados, execute apenas o que foi pedido. Evite reformatar o código inteiro, aplicar otimizações não solicitadas ou remover comentários/logs inseridos pelo usuário, a menos que explicitamente instruído. Mantenha a integridade da implementação original.

### Tratamento de Tools (Adapters)
- As ferramentas (`TOOLS` em `ai_agent.py`) são definidas como dicionários (formato compatível com a OpenAI).
- Cada serviço (ex: `GeminiService`) deve implementar um **Adapter** interno no método `generate_with_tools` para traduzir esses dicionários para o formato específico da sua biblioteca.

### Importações
- **Proibido**: Importações circulares.
- **Preferência**: Importações locais (dentro de métodos) para quebrar ciclos de importação se necessário.
- **Nível de Módulo**: Evite importar módulos que dependam de você no topo do arquivo.

## 3. RoadMap de Refatoração (Ver TODO.md)
- [ ] Refatoração para OO (Models/Repositories/Engines).
