# Estimativas comerciais

O gerador é determinístico, em Python, sem API de IA. Ele identifica entregas
por regras de texto e calcula faixas preliminares. Não interpreta linguagem com
a precisão de um profissional nem garante o preço correto de toda vaga.

As premissas estão em `config/pricing.json`: R$ 100 por hora de trabalho,
mínimo de R$ 500, seis horas produtivas por dia para a equipe inteira, 20% de
testes, 25% de reserva e dois dias úteis para revisão. Esses números são
premissas internas ajustáveis, não uma média de mercado pesquisada. Não se
pressupõe que dois desenvolvedores produzam dezesseis horas por dia em paralelo.

Cada entrega possui uma faixa de horas. Somam-se alinhamento, documentação,
testes e reserva. O prazo converte dias úteis em dias corridos aproximados;
feriados, fila de projetos e atrasos do cliente precisam de ajuste manual.

O campo da oferta corresponde ao valor do trabalho da equipe, antes de seus
impostos e despesas. A simulação de oferta final divide esse valor por
`1 - fee_fraction`. O padrão de 20% é configurável: sempre confira a oferta final
calculada no site. A taxa não é mencionada na proposta ao cliente.

Referências oficiais consultadas em 17/09/2026:
- https://www.99freelas.com.br/como-funciona
- https://99freelas.zendesk.com/hc/pt-br/articles/1500007214242-Como-enviar-propostas

Escopo curto, desconhecido, amplo, legado, integrações, especialidades não
confirmadas, exclusões e quantidades relevantes geram perguntas. O orçamento
anunciado nunca reduz automaticamente a estimativa; negocia-se o escopo.
Faixas internas continuam disponíveis, mas preço/prazo de envio ficam vazios
até esclarecimento. Respostas do cliente ainda precisam ser incorporadas
manualmente ao escopo e avaliadas novamente.

O navegador deve localizar uma descrição isolada do anúncio. Se os seletores
não corresponderem ao site, ele informa o problema e não usa o texto completo
da página como se fosse escopo. Os seletores de restrição/Premium dependem do
HTML da plataforma e precisam de validação em navegação real; não há garantia
de detectar todo selo apenas por sua cor.

As propostas apresentam a equipe, entregas, validação, negociação e custos
externos na conta do cliente. Não apresentam experiência inventada, graduação,
links ou dados de contato. Os exemplos dos primeiros envios são contexto
comercial, não contratos concluídos nem evidência de produtividade real.
