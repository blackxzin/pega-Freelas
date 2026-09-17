# Automation

Modos MANUAL, SEMI_AUTO e AUTO são suportados por configuração. Envio automático exige capability `authorized_send`, validação aprovada, score/confiança mínimos, limites por hora/dia e kill switch desligado. DRY_RUN nunca envia.

## Navegador

`ProposalBrowserAutomation` só abre vaga HTTPS e preenche proposta com validação `PASSED`. O adaptador não realiza login, não contorna CAPTCHA/anti-bot e não envia nada sem aprovação explícita do usuário e autorização do provider. O teste Playwright usa exclusivamente formulário HTML mock local: `npm run test:browser`.

Recursos Premium, Pro, compra, assinatura e turbinar ficam bloqueados por padrão em `BrowserActionPolicy`. Projetos identificados como Premium não entram na lista de elegíveis.

## Caça assistida no Chromium

`node scripts/interactive_hunt.mjs` abre Chromium visível, aguarda login manual,
coleta links públicos da listagem, ignora marcadores Premium/bandeira dourada e
preenche os campos da vaga. O clique final só ocorre após digitar `ENVIAR` para
cada vaga. O fluxo não contorna CAPTCHA, não injeta credenciais e não usa API de
IA externa.
