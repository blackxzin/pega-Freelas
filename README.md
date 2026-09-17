# FreelaHunter AI

Plataforma segura de descoberta, análise e geração de propostas para freelancing. O bootstrap inclui providers mock, normalização, deduplicação por conteúdo, filtros baratos, análise determinística substituível por AI provider, matching de portfólio, validação, preço, política de envio, SQLite e worker.

## Executar

```bash
python scripts/demo.py
python scripts/hunt.py --provider mock
python scripts/e2e.py
python scripts/worker.py
python -m pytest
npm install
npm run test:browser
```

API opcional:

```bash
python -m pip install -r requirements-api.txt
ADMIN_TOKEN='defina-um-token-forte' uvicorn freelahunter.api:create_app --factory --host 127.0.0.1 --port 8000
```

O provider HTTP (`HttpJobProvider`) aceita apenas feeds JSON via HTTPS e somente
consulta vagas. Envio continua separado, protegido por `DRY_RUN`, kill switch,
provider autorizado e aprovação explícita.

Defaults são `DRY_RUN=true`, `AUTO_SEND=false`, `AUTO_SEND_KILL_SWITCH=true`. Somente `AuthorizedMockProvider` declara envio autorizado. Integrações reais devem implementar `JobProvider`/`ProposalSender` sem bypass de CAPTCHA, Cloudflare ou rate limits.

Arquitetura detalhada: `docs/ARCHITECTURE.md`, `docs/AUTOMATION.md`, `docs/SECURITY.md`.

## Navegador

`freelahunter.browser_automation.ProposalBrowserAutomation` aceita apenas URLs HTTPS e preenche somente propostas validadas. Submissão exige aprovação explícita e provider autorizado. Adaptadores de Chrome/Playwright devem respeitar termos da plataforma, CAPTCHA e rate limits; testes não usam login, credenciais ou envio externo.
