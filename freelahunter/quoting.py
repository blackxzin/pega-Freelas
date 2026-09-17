"""Explainable preliminary estimates, not a market-price oracle."""
import json
import math
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.lower())
                   if not unicodedata.combining(c))


# Person-hours for bounded deliverables; rate is an internal assumption.
RULES = [
    ('landing page', r'landing page|pagina unica', 12, 24),
    ('site institucional', r'site institucional|site simples|website', 20, 40),
    ('blog e gerenciamento de conteúdo', r'wordpress|\bblog\b', 20, 40),
    ('API e persistência', r'\bapi\b|fastapi|backend|back-end', 24, 48),
    ('interface web', r'frontend|front-end|\breact\b|next\.?js', 24, 48),
    ('automação de fluxo', r'automacao|\bn8n\b|\bbot\b', 16, 32),
    ('autenticação e permissões', r'login|autenticacao|permissoes', 12, 24),
    ('integrações externas', r'integrac|webhook', 16, 40),
    ('pagamentos e conciliação', r'pagamento|checkout|\bpix\b|stripe', 20, 48),
    ('agenda e reservas', r'agendamento|reservas|agenda online', 20, 40),
    ('relatórios e painel', r'relatorio|dashboard|painel administrativo', 16, 32),
    ('migração e refatoração', r'migracao|refator|legado', 24, 64),
    ('arquitetura multiempresa', r'\bsaas\b|marketplace|multi.?tenant', 40, 80),
    ('aplicativo mobile', r'android|\bios\b|aplicativo mobile', 60, 120),
    ('avaliação de IA e dados', r'\bia\b|inteligencia artificial|lora|comfyui', 24, 64),
]


def build_quote(snapshot, profile, settings=None):
    if settings is None:
        settings = json.loads((ROOT / 'config/pricing.json').read_text())
    for key in ('hourly_rate', 'minimum_price', 'productive_team_hours_per_day'):
        if not math.isfinite(settings[key]) or settings[key] <= 0:
            raise ValueError(f'Invalid {key}')
    if not 0 <= settings['fee_fraction'] < 1:
        raise ValueError('Invalid fee_fraction')
    for key in ('risk_buffer', 'qa_fraction', 'feedback_business_days'):
        if not math.isfinite(settings[key]) or settings[key] < 0:
            raise ValueError(f'Invalid {key}')
    title = ' '.join(str(snapshot.get('title', '')).split())[:200]
    description = str(snapshot.get('description', ''))
    text = normalized(title + ' ' + description)
    tasks = [dict(deliverable=name, hours_min=low, hours_max=high)
             for name, pattern, low, high in RULES if re.search(pattern, text)]
    questions = []
    if len(description.split()) < 35 or not tasks:
        questions.append('Quais são as funcionalidades, entradas, saídas e critérios de aceite desta etapa?')
    if re.search(r'integrac|\bapi\b|webhook|automacao', text):
        questions.append('Quais sistemas serão integrados e já existem documentação, acessos e exemplos de dados?')
    if re.search(r'legado|refator|migracao|correc|\bbug\b', text):
        questions.append('Podemos avaliar o código atual e reproduzir o problema antes de fechar o valor?')
    if re.search(r'\bsaas\b|marketplace|completo|\bia\b|lora|comfyui', text):
        questions.append('Quais funcionalidades entram no primeiro MVP e quais ficam para etapas posteriores?')
    if re.search(r'wordpress|libras|lora|comfyui|android|\bios\b', text):
        questions.append('Precisamos confirmar internamente a experiência necessária nessa especialidade.')
    if re.search(r'\bsem\b|nao precisa|nao incluir|ja existe|ja esta pronto|apenas corrigir', text):
        questions.append('Quais partes já estão prontas e quais entregas devem ficar fora do orçamento?')
    quantities = re.findall(r'\b(\d+)\s+(?:telas|paginas|integracoes|endpoints|usuarios|produtos)\b', text)
    if any(int(value) > 3 for value in quantities):
        questions.append('Podemos detalhar as telas, integrações e volumes para estimar cada entrega?')
    blocked = snapshot.get('has_gold_badge') is True or snapshot.get('is_premium') is True
    excluded = [term for term in profile.excluded_jobs if normalized(term) in text]
    if blocked or excluded:
        return dict(action='skip', reason='Vaga restrita ou excluída pelo perfil.', suggested_price=None,
                    estimated_days=None, questions=[], breakdown=tasks)
    if not tasks:
        low = high = None
    else:
        tasks.append(dict(deliverable='alinhamento, documentação e entrega', hours_min=6, hours_max=12))
        base_low = sum(t['hours_min'] for t in tasks)
        base_high = sum(t['hours_max'] for t in tasks)
        qa = dict(deliverable='testes e revisão', hours_min=math.ceil(base_low * settings['qa_fraction']),
                  hours_max=math.ceil(base_high * settings['qa_fraction']))
        tasks.append(qa)
        low = math.ceil((base_low + qa['hours_min']) * (1 + settings['risk_buffer']))
        high = math.ceil((base_high + qa['hours_max']) * (1 + settings['risk_buffer']))
    prices = ([math.ceil(max(settings['minimum_price'], h * settings['hourly_rate']) / 50) * 50
               for h in (low, high)] if low is not None else None)
    days = ([math.ceil((math.ceil(h / settings['productive_team_hours_per_day']) +
                       settings['feedback_business_days']) * 7 / 5) for h in (low, high)]
            if low is not None else None)
    totals = [round(p / (1 - settings['fee_fraction']), 2) for p in prices] if prices else None
    budget = snapshot.get('budget_max')
    if isinstance(budget, (int, float)) and totals and budget < totals[0]:
        questions.append('O orçamento permite reduzir o escopo para uma primeira etapa ou ajustar o valor?')
    deadline = snapshot.get('deadline_days')
    if isinstance(deadline, (int, float)) and days and deadline < days[1]:
        questions.append('Há flexibilidade no prazo ou podemos priorizar uma entrega menor?')
    action = 'question' if questions else 'proposal'
    opening = f'Olá! Somos uma equipe de dois desenvolvedores full stack e temos interesse no projeto “{title}”.'
    question = (opening + ' ' + ' '.join(questions) +
                ' Podemos combinar o preço conforme o escopo e as prioridades. '
                'Custos de APIs, hospedagem e serviços pagos ficam nas contas do cliente.')
    scope = '; '.join(t['deliverable'] for t in tasks[:5])
    message = (opening + f' Pelo anúncio, a entrega envolve {scope}. '
               'Organizamos o trabalho em alinhamento dos requisitos, implementação, testes e entrega documentada. '
               'Validamos os fluxos principais e combinamos os critérios de aceite antes de iniciar. '
               'O prazo começa após recebermos os acessos, materiais e a confirmação do escopo. '
               'Novas funcionalidades são orçadas separadamente. Podemos combinar o preço conforme o escopo e as prioridades. '
               'Nossa proposta cobre desenvolvimento e configuração; APIs, hospedagem, domínio e serviços pagos ficam nas contas do cliente.')
    if action == 'proposal':
        message += f' Para esse escopo, estimamos até {days[1]} dias corridos, incluindo testes e uma rodada de revisão.'
    return dict(action=action, subject=f'Proposta: {title}', message=message, question=question,
                suggested_price=prices[1] if prices and action == 'proposal' else None,
                estimated_days=days[1] if days and action == 'proposal' else None,
                estimated_hours=high, hours_range=[low, high], price_range=prices,
                client_total_range=totals, days_range=days, questions=questions, breakdown=tasks,
                assumptions=settings, estimate_type='preliminar por regras; validar escopo e oferta final no site')
