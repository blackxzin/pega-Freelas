# FreelaHunter AI

Plataforma segura de descoberta, análise e geração de propostas para freelancing. O bootstrap inclui providers mock, normalização, deduplicação por conteúdo, filtros baratos, análise determinística substituível por AI provider, matching de portfólio, validação, preço, política de envio, SQLite e worker.

## Executar

```bash
python scripts/demo.py
python scripts/hunt.py --provider mock
python scripts/e2e.py
python scripts/worker.py
```

Defaults são `DRY_RUN=true`, `AUTO_SEND=false`, `AUTO_SEND_KILL_SWITCH=true`. Somente `AuthorizedMockProvider` declara envio autorizado. Integrações reais devem implementar `JobProvider`/`ProposalSender` sem bypass de CAPTCHA, Cloudflare ou rate limits.

Arquitetura detalhada: `docs/ARCHITECTURE.md`, `docs/AUTOMATION.md`, `docs/SECURITY.md`.
