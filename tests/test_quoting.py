import json
import pytest
from freelahunter.core import ProfileService, PriceEstimator
from freelahunter.quoting import build_quote, ROOT


def quote(title, description='', **kwargs):
    return build_quote(dict(title=title, description=description, **kwargs), ProfileService().load())


def test_vague_scope_gets_question_without_binding_amount():
    result = quote('Automação Python', 'Quero automatizar meu negócio.')
    assert result['action'] == 'question'
    assert result['suggested_price'] is None
    assert result['estimated_days'] is None
    assert result['price_range'][0] > 700


def test_complex_scope_takes_more_time_than_landing_page():
    simple = quote('Landing page')
    complex_job = quote('Marketplace SaaS com login, pagamentos, dashboard e integração API')
    assert complex_job['hours_range'][0] > simple['hours_range'][1]
    assert complex_job['days_range'][1] > simple['days_range'][1]
    assert complex_job['action'] == 'question'


def test_low_budget_does_not_lower_actual_estimate():
    initial = quote('API Python', budget_max=100000)
    cheap = quote('API Python', budget_max=100)
    assert cheap['price_range'] == initial['price_range']
    assert any('orçamento' in q for q in cheap['questions'])
    assert PriceEstimator(hourly_rate=100, minimum_project_price=500).estimate(20, budget_max=100)[0] == 2000


def test_fee_is_fraction_of_final_amount():
    result = quote('Landing page')
    assert result['client_total_range'][0] == result['price_range'][0] / .8


def test_proposal_has_no_fabricated_experience_and_has_negotiation():
    description = ('Uma landing page responsiva com apresentação, serviços e contato. '
                   'Fornecemos layout aprovado, textos, imagens e hospedagem. '
                   'Entregar arquivos HTML e CSS, formulário apenas visual e botões com links. '
                   'Aceite por comparação do layout em celular e desktop, com uma revisão.')
    result = quote('Landing page', description)
    assert result['action'] == 'proposal'
    assert result['estimated_days'] > 1
    assert 'combinar o preço' in result['message']
    assert 'contas do cliente' in result['message']
    assert 'experiência comprovável' not in result['message']
    assert 'estudante' not in result['message']


@pytest.mark.parametrize('extra', [{'has_gold_badge': True}, {'is_premium': True}])
def test_restricted_jobs_skipped(extra):
    assert quote('API Python', **extra)['action'] == 'skip'


def test_unknown_work_cannot_get_invented_quote():
    result = quote('Preciso de ajuda', 'Explico depois')
    assert result['price_range'] is None
    assert result['action'] == 'question'


def test_invalid_configuration_rejected():
    settings = json.loads((ROOT / 'config/pricing.json').read_text())
    settings['productive_team_hours_per_day'] = 0
    with pytest.raises(ValueError):
        build_quote({'title': 'API'}, ProfileService().load(), settings)


def test_pipeline_does_not_send_unresolved_scope():
    from freelahunter.core import AuthorizedMockProvider, Database, Job, MockSender, run_pipeline
    sender = MockSender()
    result = run_pipeline(AuthorizedMockProvider([Job('API Python', 'Integrar sistemas',
        external_id='unknown', budget_max=20000, skills=['Python', 'FastAPI', 'SQL'])]),
        Database(':memory:'), sender=sender, auto_send=True, dry_run=False, kill_switch=False)
    assert result['review'] == 1
    assert result['sent'] == 0
    assert not sender.sent
