import threading
from datetime import datetime, timedelta, timezone

from freelahunter.core import (
    AuthorizedMockProvider,
    Database,
    Job,
    MockSender,
    run_pipeline,
)


DESCRIPTION = (
    'Criar uma landing page responsiva com apresentação dos serviços, depoimentos e contato. '
    'Fornecemos layout aprovado, textos e imagens finais. A entrega inclui HTML e CSS, '
    'publicação na hospedagem do cliente e uma rodada de revisão com comparação visual em desktop e celular.'
)


def sendable_job(external_id, client_key=''):
    return Job(
        f'Landing page {external_id}', DESCRIPTION, external_id=str(external_id),
        url=f'https://mock.test/jobs/{external_id}', budget_min=500,
        budget_max=20000, skills=['Python', 'FastAPI', 'SQL'], client_key=client_key,
    )


def test_only_one_concurrent_worker_can_reserve_sending(tmp_path):
    db = Database(str(tmp_path / 'concurrent-claim.db'))
    db.register_proposal(None, 'same-key', 'Proposta', 'mensagem', 1000, 'API', 'client-1')
    barrier = threading.Barrier(2)
    results = []

    def claim():
        barrier.wait(timeout=2)
        results.append(db.claim_send('same-key'))

    workers = [threading.Thread(target=claim) for _ in range(2)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=2)

    assert sorted(results) == [False, True]
    assert db.conn.execute(
        'SELECT status FROM proposals WHERE idempotency_key=?', ('same-key',)
    ).fetchone() == ('SENDING',)
    assert db.already_sent('same-key') is True


def test_reregistering_a_sending_proposal_cannot_release_reservation(tmp_path):
    db = Database(str(tmp_path / 'sending-reservation.db'))
    proposal_id = db.register_proposal(None, 'same-key', 'Proposta', 'primeira', 1200, 'API', 'client-1')
    assert db.claim_send('same-key') is True

    db.register_proposal(None, 'same-key', 'Proposta atualizada', 'tentativa repetida', 900, 'API', 'client-1')

    assert db.conn.execute(
        'SELECT id,status,suggested_price FROM proposals WHERE idempotency_key=?', ('same-key',)
    ).fetchone() == (proposal_id, 'SENDING', 900)
    assert db.claim_send('same-key') is False


def test_uncertain_sender_attempt_is_not_repeated_on_next_poll(monkeypatch):
    monkeypatch.setenv('STRUCTURED_LOGS', 'false')

    class NoReceiptSender(MockSender):
        def __init__(self):
            super().__init__()
            self.attempts = 0

        def send(self, proposal):
            self.attempts += 1
            return {}

    sender = NoReceiptSender()
    provider = AuthorizedMockProvider([sendable_job('uncertain')])
    db = Database(':memory:')

    first = run_pipeline(provider, db, auto_send=True, dry_run=False, kill_switch=False, sender=sender)
    second = run_pipeline(provider, db, auto_send=True, dry_run=False, kill_switch=False, sender=sender)

    assert first['errors'] == 1
    assert first['sent'] == 0
    assert second['duplicates'] == 1
    assert second['sent'] == 0
    assert sender.attempts == 1
    assert db.conn.execute('SELECT status FROM proposals').fetchone() == ('SENDING',)


def test_client_limit_allows_one_send_and_reviews_the_next_job(monkeypatch):
    monkeypatch.setenv('STRUCTURED_LOGS', 'false')
    sender = MockSender()
    jobs = [sendable_job('one', 'same-client'), sendable_job('two', 'same-client')]

    result = run_pipeline(
        AuthorizedMockProvider(jobs), Database(':memory:'), auto_send=True,
        dry_run=False, kill_switch=False, sender=sender, max_per_hour=10, max_per_day=10,
    )

    assert result['sent'] == 1
    assert result['review'] == 1
    assert len(sender.sent) == 1


def test_client_limit_counts_sending_but_expires_sent_records(tmp_path):
    db = Database(str(tmp_path / 'client-window.db'))
    db.register_proposal(None, 'sending-key', 'Proposta', 'mensagem', 1000, 'API', 'client-1')
    db.claim_send('sending-key')
    assert db.client_send_gate('client-1') == (False, 'limite por cliente atingido (1/1 em 24h)')

    db.register_proposal(None, 'sent-key', 'Proposta', 'mensagem', 1000, 'API', 'client-2')
    db.mark_sent('sent-key', 'external-1')
    old_sent_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    db.conn.execute('UPDATE proposals SET sent_at=? WHERE idempotency_key=?', (old_sent_at, 'sent-key'))
    db.conn.commit()

    assert db.client_send_gate('client-2') == (True, 'ok')
