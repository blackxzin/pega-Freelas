import json
from io import BytesIO

import pytest

from freelahunter.core import *
from freelahunter.providers import HttpJobProvider

def job(): return Job('Landing page', 'Criar uma landing page responsiva com apresentação dos serviços, depoimentos e contato. Fornecemos layout aprovado, textos e imagens finais. A entrega inclui HTML e CSS, publicação na hospedagem do cliente e uma rodada de revisão com comparação visual em desktop e celular.', external_id='1', url='https://x/1', skills=['Python','FastAPI','SQL'], budget_min=500, budget_max=20000)

def test_authorized_autosend_is_idempotent():
    db=Database(':memory:'); sender=MockSender(); p=AuthorizedMockProvider([job()])
    first=run_pipeline(p,db,auto_send=True,dry_run=False,kill_switch=False,sender=sender)
    second=run_pipeline(p,db,auto_send=True,dry_run=False,kill_switch=False,sender=sender)
    assert first['sent']==1 and second['duplicates']==1 and len(sender.sent)==1

def test_safety_guards_block_send():
    for kwargs in ({'dry_run':True},{'auto_send':False},{'kill_switch':True}):
        sender=MockSender()
        opts={'auto_send':True,'dry_run':False,'kill_switch':False,'sender':sender}; opts.update(kwargs)
        db=Database(':memory:'); s=run_pipeline(AuthorizedMockProvider([job()]),db,**opts)
        assert s['sent']==0 and not sender.sent

def test_unauthorized_provider_never_sends():
    sender=MockSender(); s=run_pipeline(MockProvider([job()]),Database(':memory:'),auto_send=True,dry_run=False,kill_switch=False,sender=sender)
    assert s['sent']==0

def test_validator_blocks_placeholders():
    p=ProposalDraft(1,'x','TODO [CLIENT]',1,None,[])
    assert ProposalValidator().validate(p,Profile()) [0]=='FAILED'

def test_profile_loads_team_and_client_cost_rules(tmp_path):
    profile_path = tmp_path / 'profile.yaml'
    profile_path.write_text(
        'headline: Desenvolvedor Full Stack\n'
        'team_description: equipe de dois desenvolvedores full stack\n'
        'client_pays_paid_services: true\n'
        'education: ""\n',
        encoding='utf-8',
    )

    profile = ProfileService(str(profile_path)).load()
    proposal = ProposalGenerator().generate(job(), AIService().analyze(job(), profile, []), profile, [])

    assert 'estudante' not in profile.headline.lower()
    assert profile.team_description == 'equipe de dois desenvolvedores full stack'
    assert profile.client_pays_paid_services is True
    assert 'equipe de dois desenvolvedores full stack' in proposal.message
    assert 'contas do cliente' in proposal.message


def test_pipeline_applies_profile_job_rules():
    profile = Profile(
        preferred_jobs=['API'],
        excluded_jobs=['Premium'],
        minimum_budget=500,
    )
    jobs = [
        Job('API pública', 'Criar API REST', external_id='good', url='https://mock/good', budget_max=800),
        Job('API Premium', 'Criar API Premium', external_id='premium', url='https://mock/premium', budget_max=800),
    ]

    stats = run_pipeline(MockProvider(jobs), Database(':memory:'), profile=profile)

    assert stats['found'] == 2
    assert stats['filtered'] == 1
    assert stats['proposals'] == 1


def test_filter_matches_whole_keywords_and_accents():
    service = FilterService(included_keywords=['API'], excluded_keywords=['Premium'])
    assert service.accepts(Job('Capital de giro', 'Sistema web', external_id='capital')) is False
    assert service.accepts(Job('API pública', 'Integração com automação', external_id='api')) is True
    assert service.accepts(Job('API premiumizada', 'API REST', external_id='premiumized')) is True


def test_analysis_uses_skills_found_in_description_when_feed_omits_skills():
    analyzed = AIService().analyze(
        Job('API FastAPI', 'Criar API com Python, FastAPI e SQL.', external_id='text-only'),
        ProfileService().load(), [],
    )
    assert {'python', 'fastapi'} <= set(analyzed.matched_skills)
    assert analyzed.score > 50


def test_database_migration_preserves_proposals_and_tracks_outcome(tmp_path):
    db = Database(str(tmp_path / 'tracking.db'))
    proposal_id = db.register_proposal(None, 'key-1', 'Proposta', 'mensagem', 1200, 'API', 'client-1')
    db.mark_sent('key-1', 'external-1', '42')
    db.record_message('42', 'Confirmo duas telas.', is_scope_context=True)
    db.set_proposal_outcome(proposal_id, 'accepted')
    row = db.conn.execute('SELECT outcome_status,conversation_id,price_band FROM proposals WHERE id=?', (proposal_id,)).fetchone()
    assert row == ('accepted', '42', 'R$ 1.000–2.499')
    assert db.conn.execute('SELECT COUNT(*) FROM conversation_messages').fetchone()[0] == 1
    assert db.conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'


def test_dynamic_quote_uses_complexity_urgency_and_history():
    from freelahunter.quoting import build_quote
    profile = ProfileService().load()
    base = build_quote({'title': 'API', 'description': 'Criar API simples.'}, profile)
    adjusted = build_quote({'title': 'API', 'description': 'Criar API com quatro integrações e seis telas.',
                            'integrations_count': 4, 'screens_count': 6, 'deadline_days': 2,
                            'client_history': {'recurring': True, 'good_history': True}}, profile)
    assert adjusted['pricing_factors']['multiplier'] > 1
    assert adjusted['price_range'][1] > base['price_range'][1]


def test_pause_circuit_blocks_after_rejections(tmp_path):
    db = Database(str(tmp_path / 'pause.db'))
    for number in range(2):
        proposal_id = db.register_proposal(None, f'key-{number}', 'Proposta', 'mensagem', 1000, 'API', 'client')
        db.mark_sent(f'key-{number}', f'ext-{number}')
        db.set_proposal_outcome(proposal_id, 'rejected')
    assert db.get_automation_state()[0] == 1
    assert db.send_gate()[0] is False


def test_runtime_control_kill_switch_blocks_authorized_send():
    control = RuntimeControl(False)
    control.set_kill_switch(True)
    sender = MockSender()

    stats = run_pipeline(
        AuthorizedMockProvider([job()]),
        Database(':memory:'),
        auto_send=True,
        dry_run=False,
        kill_switch=False,
        runtime_control=control,
        sender=sender,
    )

    assert stats['sent'] == 0
    assert not sender.sent


def test_http_provider_reads_json_feed_without_send(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({'jobs': [{'title': 'API', 'description': 'Criar API', 'external_id': '1'}]}).encode()

    monkeypatch.setattr('freelahunter.providers.urlopen', lambda request, timeout: Response())
    provider = HttpJobProvider('https://feed.example/jobs', name='feed')

    jobs = provider.search()

    assert len(jobs) == 1
    assert jobs[0].title == 'API'
    assert jobs[0].platform == 'feed'
    assert provider.capabilities.authorized_send is False


def test_http_provider_rejects_non_https():
    with pytest.raises(ValueError, match='HTTPS'):
        HttpJobProvider('http://feed.example/jobs')
