# Security

Segredos ficam em `.env` (nunca no banco, logs ou frontend). Não há automação de interfaces proibidas nem evasão de anti-bot. Comece sempre em dry-run/semi-auto e habilite produção explicitamente.

O modo `AUTO` é opt-in e mantém limites de 3 propostas por hora e 10 por dia,
idempotência, validação de conteúdo e kill switch. O circuito de pausa bloqueia
novos envios quando a taxa de rejeição ou a sequência de propostas sem resposta
ultrapassa a configuração. O smoke test real é somente leitura.
