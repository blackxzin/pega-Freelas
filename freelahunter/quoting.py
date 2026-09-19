"""Explainable preliminary estimates, not a market-price oracle."""
import json
import math
import re
import unicodedata
from pathlib import Path

from .knowledge import commercial_advisories

ROOT = Path(__file__).resolve().parents[1]


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value.lower())
                   if not unicodedata.combining(c))


def format_brl(value):
    return f'R$ {value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


# Person-hours for bounded deliverables; rate is an internal assumption.
RULES = [
    ('landing page', r'landing page|pagina unica', 12, 24),
    ('site institucional', r'site institucional|site simples|website', 20, 40),
    ('site em CMS ou blog', r'wordpress|\bblog\b', 20, 40),
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
    price_floor = settings.get('proposal_price_floor', settings['minimum_price'])
    price_ceiling = settings.get('proposal_price_ceiling', float('inf'))
    valid_floor = isinstance(price_floor, (int, float)) and math.isfinite(price_floor) and price_floor > 0
    valid_ceiling = isinstance(price_ceiling, (int, float)) and price_ceiling > 0 and (math.isfinite(price_ceiling) or math.isinf(price_ceiling))
    if not valid_floor or not valid_ceiling or price_ceiling < price_floor:
        raise ValueError('Invalid proposal price band')
    if not 0 <= settings['fee_fraction'] < 1:
        raise ValueError('Invalid fee_fraction')
    for key in ('risk_buffer', 'qa_fraction', 'feedback_business_days'):
        if not math.isfinite(settings[key]) or settings[key] < 0:
            raise ValueError(f'Invalid {key}')
    adjustments = settings.get('adjustments', {})
    defaults = {
        'complexity_per_integration': 0.0, 'complexity_per_screen': 0.0,
        'urgent_deadline_days': 0, 'urgent_multiplier': 0.0,
        'recurring_client_multiplier': 0.0, 'good_history_multiplier': 0.0,
        'min_multiplier': 1.0, 'max_multiplier': 1.0,
    }
    adjustments = {key: adjustments.get(key, value) for key, value in defaults.items()}
    for key, value in adjustments.items():
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f'Invalid adjustments.{key}')
    if adjustments['min_multiplier'] <= 0 or adjustments['max_multiplier'] < adjustments['min_multiplier']:
        raise ValueError('Invalid adjustment multiplier bounds')
    title = ' '.join(str(snapshot.get('title', '')).split())[:200]
    description = str(snapshot.get('description', ''))
    confirmed_context = [str(item).strip() for item in snapshot.get('confirmed_context', []) if str(item).strip()]
    if confirmed_context:
        description += '\nRestrições confirmadas pelo cliente:\n' + '\n'.join(confirmed_context[-20:])
    text = normalized(title + ' ' + description)
    integration_count = snapshot.get('integrations_count')
    if not isinstance(integration_count, (int, float)):
        integration_count = len(re.findall(r'integrac|webhook|conexao com|terceiro', text))
    screen_count = snapshot.get('screens_count')
    if not isinstance(screen_count, (int, float)):
        quantities = re.findall(r'\b(\d+)\s+(?:telas|paginas|landing pages|endpoints)\b', text)
        screen_count = sum(int(value) for value in quantities)
        if screen_count == 0:
            screen_count = len(re.findall(r'\b(?:tela|pagina|dashboard|painel)\b', text))
    factor = 1.0 + float(integration_count) * adjustments['complexity_per_integration']
    factor += float(screen_count) * adjustments['complexity_per_screen']
    deadline = snapshot.get('deadline_days')
    if isinstance(deadline, (int, float)) and adjustments['urgent_deadline_days'] > 0 and deadline <= adjustments['urgent_deadline_days']:
        factor += adjustments['urgent_multiplier']
    history = snapshot.get('client_history') or {}
    if history.get('recurring'):
        factor += adjustments['recurring_client_multiplier']
    if history.get('good_history'):
        factor += adjustments['good_history_multiplier']
    factor = min(adjustments['max_multiplier'], max(adjustments['min_multiplier'], factor))
    effective_hourly_rate = settings['hourly_rate'] * factor
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
    if re.search(r'pagamento|checkout|\bpix\b|boleto|cartao', text):
        questions.append('Qual gateway de pagamento será usado e quais meios, regras de cobrança, repasse e conciliação entram no escopo?')
    if re.search(r'plataforma', text) and not re.search(r'criterios de aceite|fluxos detalhados|documentacao funcional', text):
        questions.append('Quais perfis de usuário, telas e fluxos entram na primeira entrega da plataforma?')
    if re.search(r'landing pages', text):
        questions.append('Quantas landing pages serão entregues e o cliente fornecerá layout, textos, imagens, domínio e regras dos formulários?')
    elif re.search(r'site profissional|website', text) and not re.search(r'\b\d+\s+paginas|pagina unica|layout aprovado', text):
        questions.append('Quantas páginas e seções entram no site e quem fornecerá layout, textos, imagens e formulários?')
    if re.search(r'libras|lora|comfyui|android|\bios\b', text):
        questions.append('Precisamos confirmar internamente a experiência necessária nessa especialidade.')
    if re.search(r'\bsem\b|nao precisa|nao incluir|ja existe|ja esta pronto|apenas corrigir', text):
        questions.append('Quais partes já estão prontas e quais entregas devem ficar fora do orçamento?')
    quantities = re.findall(r'\b(\d+)\s+(?:telas|paginas|landing pages|integracoes|endpoints|usuarios|produtos)\b', text)
    if any(int(value) > 3 for value in quantities):
        questions.append('Podemos detalhar as telas, integrações e volumes para estimar cada entrega?')
    blocked = snapshot.get('has_gold_badge') is True or snapshot.get('is_premium') is True
    excluded = [term for term in profile.excluded_jobs
                if re.search(r'(?<!\w)' + re.escape(normalized(term)) + r'(?!\w)', text)]
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
    raw_prices = ([math.ceil(max(settings['minimum_price'], h * effective_hourly_rate) / 50) * 50
                   for h in (low, high)] if low is not None else None)
    prices = ([min(price_ceiling, max(price_floor, price)) for price in raw_prices]
              if raw_prices else None)
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
    advisory = commercial_advisories(snapshot, settings, high, prices[1] if prices else None)
    if 'off_platform_contact' in advisory['risk_ids']:
        return dict(action='skip', reason='Pedido de contato fora da plataforma exige revisão manual.',
                    suggested_price=None, estimated_days=None, questions=[], breakdown=tasks,
                    knowledge=advisory)
    action = 'question' if questions else 'proposal'
    client = ' '.join(str(snapshot.get('client', '')).split())[:80]
    greeting = f'Olá, {client}!' if client else 'Olá!'
    opening = (f'{greeting} Somos uma equipe de dois desenvolvedores full stack que trabalham juntos e temos interesse '
               f'no projeto “{title}”.')
    question = (opening + ' ' + ' '.join(questions) +
                ' Depois desses detalhes, podemos combinar um valor justo conforme o escopo e as prioridades. '
                'Custos de APIs, hospedagem e serviços pagos ficam nas contas do cliente.')
    scope = '; '.join(t['deliverable'] for t in tasks[:5])
    message = (opening + f' Entendemos que a entrega envolve {scope}. '
               'Propomos executar em etapas verificáveis: alinhamento dos requisitos, implementação, testes e entrega documentada. '
               'Validamos os fluxos principais e combinamos os critérios de aceite antes de iniciar. '
               'O prazo começa após recebermos os acessos, materiais e a confirmação do escopo. '
               'Novas funcionalidades são orçadas separadamente. '
               'Nossa proposta cobre desenvolvimento e configuração; APIs, hospedagem, domínio e serviços pagos ficam nas contas do cliente.')
    if action == 'proposal':
        message += (f' Como proposta inicial para esse escopo, indicamos {format_brl(prices[1])} e prazo de até '
                    f'{days[1]} dias corridos, incluindo testes e uma rodada de revisão. Esse é um valor de '
                    'referência. O valor pode ser combinado e o preço pode ser negociado conforme os detalhes finais, '
                    'o escopo e as prioridades '
                    'do projeto. Se fizer sentido, podemos alinhar as etapas e ajustar a proposta aqui pela plataforma.')
    return dict(action=action, subject=f'Proposta: {title}', message=message, question=question,
                suggested_price=prices[1] if prices and action == 'proposal' else None,
                estimated_days=days[1] if days and action == 'proposal' else None,
                estimated_hours=high, hours_range=[low, high], price_range=prices,
                client_total_range=totals, days_range=days, questions=questions, breakdown=tasks,
                assumptions=settings, knowledge=advisory,
                estimate_type='preliminar por regras; referências de mercado são apenas sanity check',
                pricing_factors={
                    'integration_count': int(integration_count), 'screen_count': int(screen_count),
                    'multiplier': round(factor, 4), 'effective_hourly_rate': round(effective_hourly_rate, 2),
                    'client_history': history, 'confirmed_context_count': len(confirmed_context),
                })
