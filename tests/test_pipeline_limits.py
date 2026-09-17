from freelahunter.core import AuthorizedMockProvider, Database, Job, MockSender, run_pipeline


def make_job(number):
    return Job(
        f'Landing page {number}',
        'Criar uma landing page responsiva com apresentação dos serviços, depoimentos e contato. Fornecemos layout aprovado, textos e imagens finais. A entrega inclui HTML e CSS, publicação na hospedagem do cliente e uma rodada de revisão com comparação visual em desktop e celular.',
        external_id=str(number),
        url=f'https://mock.test/jobs/{number}',
        budget_min=500,
        budget_max=20000,
        skills=['Python', 'FastAPI', 'SQL'],
    )


def test_pipeline_enforces_hourly_and_daily_send_limits():
    sender = MockSender()
    result = run_pipeline(
        AuthorizedMockProvider([make_job(1), make_job(2)]),
        Database(':memory:'),
        auto_send=True,
        dry_run=False,
        kill_switch=False,
        sender=sender,
        max_per_hour=1,
        max_per_day=1,
    )
    assert result['sent'] == 1
    assert result['review'] == 1
    assert result['errors'] == 0
    assert len(sender.sent) == 1


class BrokenSender(MockSender):
    def send(self, proposal):
        return {}


def test_pipeline_records_sender_failure_without_stopping_other_jobs():
    result = run_pipeline(
        AuthorizedMockProvider([make_job(1), make_job(2)]),
        Database(':memory:'),
        auto_send=True,
        dry_run=False,
        kill_switch=False,
        sender=BrokenSender(),
        max_per_hour=10,
        max_per_day=10,
    )
    assert result['found'] == 2
    assert result['errors'] == 2
    assert result['sent'] == 0
