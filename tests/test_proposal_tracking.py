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
