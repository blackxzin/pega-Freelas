# Estimativas comerciais

O gerador é determinístico, em Python, sem API de IA. Ele identifica entregas
por regras de texto e calcula faixas preliminares. Não interpreta linguagem com
a precisão de um profissional nem garante o preço correto de toda vaga.

A base `knowledge/freelance-market-br-2026.json`, fornecida pelo usuário, é
consultiva. O bot registra alertas quando o valor/hora implícito sai da faixa de
referência, mas não altera o preço calculado para forçar encaixe nessa faixa.

As premissas estão em `config/pricing.json`: R$ 45 por hora de trabalho,
faixa calculada limitada a R$ 900–R$ 6.000, seis horas produtivas por dia para a
equipe inteira, 20% de testes, 25% de reserva e dois dias úteis para revisão.
Esses números são
premissas internas ajustáveis, não uma média de mercado pesquisada. Não se
pressupõe que dois desenvolvedores produzam dezesseis horas por dia em paralelo.

Cada entrega possui uma faixa de horas. Somam-se alinhamento, documentação,
testes e reserva. O prazo converte dias úteis em dias corridos aproximados;
feriados, fila de projetos e atrasos do cliente precisam de ajuste manual.

O campo da oferta corresponde ao valor do trabalho da equipe, antes de seus
impostos e despesas. A simulação de oferta final divide esse valor por
`1 - fee_fraction`. O padrão de 20% é configurável: sempre confira a oferta final
calculada no site. A taxa não é mencionada na proposta ao cliente.

O valor final pode aplicar fatores determinísticos configuráveis para quantidade
de integrações, quantidade de telas, urgência e histórico do cliente. O fator é
limitado por `min_multiplier`/`max_multiplier`; quando o histórico é desconhecido,
o multiplicador permanece neutro. A prioridade e o filtro de vagas não usam esse
ajuste.

Referências oficiais consultadas em 17/09/2026:
- https://www.99freelas.com.br/como-funciona
- https://99freelas.zendesk.com/hc/pt-br/articles/1500007214242-Como-enviar-propostas

Escopo curto, desconhecido, amplo, legado, integrações, especialidades não
confirmadas, exclusões e quantidades relevantes geram perguntas. Quando já há
entregas identificáveis, a mensagem de esclarecimento também informa a
estimativa inicial de preço e prazo; sem base suficiente, ambos ficam a
confirmar. O orçamento anunciado nunca reduz automaticamente a estimativa;
negocia-se o escopo. Respostas capturadas pelo monitor entram como contexto
confirmado na próxima geração; a proposta continua sujeita às travas e ao
modo de envio configurado.

O navegador deve localizar uma descrição isolada do anúncio. Se os seletores
não corresponderem ao site, ele informa o problema e não usa o texto completo
da página como se fosse escopo. Os seletores de restrição/Premium dependem do
HTML da plataforma e precisam de validação em navegação real; não há garantia
de detectar todo selo apenas por sua cor.

As propostas apresentam a equipe de dois desenvolvedores full stack, entregas,
validação, um preço e prazo iniciais pelo ponto médio da faixa calculada, com
possibilidade explícita de combinar o valor após confirmar o escopo e custos
externos na conta do cliente. Não apresentam experiência inventada, graduação,
links ou dados de contato. Os exemplos dos primeiros envios são contexto
comercial, não contratos concluídos nem evidência de produtividade real.

No Upwork, `config/upwork_pricing.json` mantém premissas separadas em USD e
faixas opcionais para EUR, GBP e BRL. A moeda é detectada no snapshot da vaga;
isso muda a unidade e a faixa configurada, mas não faz conversão cambial em
tempo real. Atualize essas premissas manualmente quando necessário.
