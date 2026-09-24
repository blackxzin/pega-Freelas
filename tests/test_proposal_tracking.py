import json
import subprocess
import sys

from freelahunter.core import Database


def run_tracking(database, *args, payload=None):
    completed = subprocess.run(
        [sys.executable, 'scripts/proposal_tracking.py', '--database', str(database), *args],
        input=json.dumps(payload) if payload is not None else None,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_tracking_register_treats_sending_as_already_sent(tmp_path):
    database = tmp_path / 'tracking.db'
    db = Database(str(database))
    db.register_proposal(None, 'same-key', 'Proposta', 'mensagem', 1000, 'API', 'client-1')
    assert db.claim_send('same-key') is True

    result = run_tracking(
        database,
        'register',
        payload={
            'idempotency_key': 'same-key',
            'title': 'API',
            'message': 'mensagem',
            'price': 1000,
            'client_key': 'client-1',
        },
    )

    assert result['already_sent'] is True


def test_tracking_key_does_not_change_when_generated_copy_changes(tmp_path):
    database = tmp_path / 'stable-key.db'
    first = run_tracking(database, 'register', payload={
        'url': 'https://mock.test/project/42?tracking=first',
        'title': 'API de pedidos',
        'message': 'primeira versão da proposta',
        'price': 1500,
        'client_key': 'https://mock.test/users/9/',
    })
    db = Database(str(database))
    db.claim_send(first['idempotency_key'])
    second = run_tracking(database, 'register', payload={
        'url': 'https://MOCK.TEST/project/42?tracking=second',
        'title': 'API de pedidos',
        'message': 'texto recalculado com novo preço',
        'price': 1800,
        'client_key': 'https://mock.test/users/9',
    })
    assert second['idempotency_key'] == first['idempotency_key']
    assert second['already_sent'] is True


def test_message_send_does_not_consume_proposal_limit(tmp_path):
    database = tmp_path / 'message-kind.db'
    result = run_tracking(database, 'register', payload={
        'url': 'https://mock.test/project/43',
        'title': 'Mensagem fallback',
        'message': 'estimativa preliminar com preço negociável',
        'price': 1800,
        'client_key': 'client-43',
        'send_kind': 'message',
    })
    run_tracking(database, 'claim', '--proposal-id', str(result['proposal_id']))
    run_tracking(database, 'sent', '--proposal-id', str(result['proposal_id']), '--external-id', 'message-43')
    db = Database(str(database))
    assert db.within_limit('send-day', 1, 86400) is True
    assert db.client_message_gate('client-43') == (
        False, 'limite de mensagens por cliente atingido (1/1 em 24h)'
    )
