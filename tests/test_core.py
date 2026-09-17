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
