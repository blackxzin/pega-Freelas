# Automation

Modos MANUAL, SEMI_AUTO e AUTO são suportados por configuração. No Chromium,
`AUTO` caça vagas, calcula preço, gera texto, preenche e envia após validação.
Envio automático exige `AUTO_SEND=true`, `DRY_RUN=false`, kill switch desligado,
validação aprovada, limites por hora/dia e circuito de pausa liberado. Defaults
continuam seguros: `DRY_RUN=true`, `AUTO_SEND=false` e kill switch ligado.

## Navegador

`ProposalBrowserAutomation` só abre vaga HTTPS e preenche proposta com validação `PASSED`. O adaptador não realiza login, não contorna CAPTCHA/anti-bot e não envia nada sem aprovação explícita do usuário e autorização do provider. O teste Playwright usa exclusivamente formulário HTML mock local: `npm run test:browser`.

Recursos Premium, Pro, compra, assinatura e turbinar ficam bloqueados por padrão em `BrowserActionPolicy`. Projetos identificados como Premium não entram na lista de elegíveis.

## Caça assistida no Chromium

`node scripts/interactive_hunt.mjs` abre Chromium visível, usa sessão autenticada
salva, coleta links públicos da listagem, ignora marcadores Premium/bandeira
dourada e preenche os campos da vaga. Em `SEMI_AUTO`, o clique final exige
`ENVIAR`; em `AUTO`, as travas fazem essa decisão. O fluxo não contorna CAPTCHA,
não injeta credenciais e não usa API de IA externa.

Ativação explícita:

```bash
AUTOMATION_MODE=AUTO AUTO_SEND=true DRY_RUN=false \
AUTO_SEND_KILL_SWITCH=false node scripts/interactive_hunt.mjs
```
