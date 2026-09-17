# Architecture

`ProviderRegistry` carrega `JobProvider`s; o pipeline normaliza `Job`, calcula SHA-256, persiste e deduplica, aplica filtros, analisa, consulta `PortfolioService`, gera e valida `ProposalDraft`, calcula preço e aplica `SendPolicyEngine`. SQLite mantém histórico e chave de idempotência única.
