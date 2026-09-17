"""Load advisory commercial knowledge without turning references into hard prices."""
import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / 'knowledge/freelance-market-br-2026.json'


@lru_cache(maxsize=4)
def load_commercial_knowledge(path=None):
    source = Path(path) if path else DEFAULT_PATH
    data = json.loads(source.read_text(encoding='utf-8'))
    if data.get('metadata', {}).get('advisory_only') is not True:
        raise ValueError('Commercial knowledge must be explicitly advisory')
    return data


def commercial_advisories(snapshot, settings, estimated_hours, suggested_price, path=None):
    knowledge = load_commercial_knowledge(path)
    notes = []
    if estimated_hours and suggested_price:
        implicit_rate = suggested_price / estimated_hours
        low, high = knowledge['pricing']['hourly_reference_brl']['general_developer']
        if implicit_rate < low:
            notes.append(f'Valor implícito de R$ {implicit_rate:.2f}/h abaixo da referência consultiva de R$ {low}/h.')
        elif implicit_rate > high:
            notes.append(f'Valor implícito de R$ {implicit_rate:.2f}/h acima da faixa geral; justificar pela complexidade.')
        else:
            notes.append(f'Valor implícito de R$ {implicit_rate:.2f}/h dentro da faixa consultiva geral.')
    text = f"{snapshot.get('title', '')} {snapshot.get('description', '')}".casefold()
    risk_ids = []
    for risk in knowledge['risk_signals']:
        if any(pattern.casefold() in text for pattern in risk['patterns']):
            risk_ids.append(risk['id'])
            notes.append(risk['guidance'])
    if estimated_hours and estimated_hours >= 40:
        notes.append('Projeto grande: preferir etapas verificáveis com entregas parciais.')
    return {
        'knowledge_id': knowledge['metadata']['id'],
        'advisory_only': True,
        'risk_ids': risk_ids,
        'notes': notes,
        'internal_hourly_rate': settings['hourly_rate'],
    }
