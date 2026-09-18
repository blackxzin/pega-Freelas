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

O navegador abre, usa uma sessão autenticada salva, ignora Premium/bandeira
dourada, lê a vaga, preenche proposta ou pergunta e calcula valor/prazo.
No modo `SEMI_AUTO`, pede `ENVIAR`; no modo `AUTO`, envia somente após todas as
travas configuráveis passarem. `BROWSER_PROFILE_DIR` pode apontar para um perfil
separado.

Monitor de respostas no Discord (sem responder clientes automaticamente):

```bash
npm run monitor:inbox
npm run smoke:selectors
python scripts/proposal_tracking.py report
python scripts/dashboard.py
```

Defina `DISCORD_WEBHOOK_URL` em `.env`. `INBOX_POLL_SECONDS` controla o intervalo
(mínimo de 20 segundos). O monitor usa a sessão manual do Chromium, alerta
somente conversa não lida do cliente e inclui link para responder dentro do
99Freelas. Falhas temporárias do Discord são repetidas com backoff; falhas de
leitura não encerram o monitor. O estado local impede alertas duplicados após
reiniciar.

Automação total (opt-in explícito): `AUTOMATION_MODE=AUTO`, `AUTO_SEND=true` e
`DRY_RUN=false`, com `AUTO_SEND_KILL_SWITCH=false`. Mesmo nesse modo continuam
valendo validação da proposta, limites por hora/dia, idempotência e circuito de
pausa. O smoke test é somente leitura; use `SMOKE_JOB_URL` para validar também
os campos da página de uma vaga.

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
