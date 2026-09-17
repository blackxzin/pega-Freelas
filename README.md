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

Caça assistida no Chromium (login manual):

```bash
MAX_JOBS=5 node scripts/interactive_hunt.mjs
```

O navegador abre, aguarda login manual, ignora Premium/bandeira dourada, lê a
vaga, preenche proposta ou pergunta, calcula valor/prazo e pede `ENVIAR` antes
do clique final. `BROWSER_PROFILE_DIR` pode apontar para um perfil separado.

API opcional:

```bash
python -m pip install -r requirements-api.txt
ADMIN_TOKEN='defina-um-token-forte' uvicorn freelahunter.api:create_app --factory --host 127.0.0.1 --port 8000
```

O provider HTTP (`HttpJobProvider`) aceita apenas feeds JSON via HTTPS e somente
consulta vagas. Envio continua separado, protegido por `DRY_RUN`, kill switch,
provider autorizado e aprovação explícita.

## Estimativas e qualidade das propostas

O fluxo Chromium usa `freelahunter/quoting.py` para decompor entregas e gerar
faixas preliminares de horas, valores e dias corridos. Configure taxa horária,
capacidade da equipe, testes e reserva em `config/pricing.json`. Essas premissas
não são uma média de mercado. Consulte `docs/PRICING.md` para fórmulas e limites.
Escopos insuficientes geram perguntas, sem preencher preço/prazo fechado.
Referências comerciais fornecidas pelo usuário ficam em
`knowledge/freelance-market-br-2026.json`. Elas servem como sanity check e
orientação de proposta; nunca substituem o cálculo por escopo e horas.
Os seletores reais do 99Freelas ainda precisam de validação; os testes locais
não comprovam funcionamento completo na conta real.

Defaults são `DRY_RUN=true`, `AUTO_SEND=false`, `AUTO_SEND_KILL_SWITCH=true`. Somente `AuthorizedMockProvider` declara envio autorizado. Integrações reais devem implementar `JobProvider`/`ProposalSender` sem bypass de CAPTCHA, Cloudflare ou rate limits.

Arquitetura detalhada: `docs/ARCHITECTURE.md`, `docs/AUTOMATION.md`, `docs/SECURITY.md`.

## Navegador

`freelahunter.browser_automation.ProposalBrowserAutomation` aceita apenas URLs HTTPS e preenche somente propostas validadas. Submissão exige aprovação explícita e provider autorizado. Adaptadores de Chrome/Playwright devem respeitar termos da plataforma, CAPTCHA e rate limits; testes não usam login, credenciais ou envio externo.
