# Architecture

`ProviderRegistry` carrega `JobProvider`s; o pipeline normaliza `Job`, calcula SHA-256, persiste e deduplica, aplica filtros, analisa, consulta `PortfolioService`, gera e valida `ProposalDraft`, calcula preço e aplica `SendPolicyEngine`. SQLite mantém histórico e chave de idempotência única.

O schema é evoluído por migração aditiva na inicialização de `Database`. Além
das tabelas originais, há eventos de proposta, mensagens de conversa, estado do
circuito de pausa e versão de schema. `proposal_tracking.py` faz a ponte entre
Chromium e SQLite para registrar proposta, envio, resposta e resultado manual.

`selectors.json` concentra seletores e fallbacks do navegador. O smoke test real
é somente leitura. `dashboard.py` gera um relatório HTML estático a partir do
SQLite.
