"""Generate one proposal/question from a job snapshot on stdin."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from freelahunter.core import ProfileService, ProposalDraft, ProposalValidator
from freelahunter.quoting import build_quote


def main() -> None:
    profile_path = Path(__file__).resolve().parents[1] / 'config/profile.yaml'
    snapshot = json.load(sys.stdin)
    profile = ProfileService(str(profile_path)).load()
    result = build_quote(snapshot, profile)
    if result.get('action') == 'proposal':
        draft = ProposalDraft(0, result.get('subject', ''), result.get('message') if result.get('action') == 'proposal' else result.get('question', ''), result.get('estimated_hours') or 0, result.get('suggested_price'), result.get('questions', []))
        status, reasons = ProposalValidator().validate(draft, profile)
        result['validation_status'] = status
        result['validation_reasons'] = reasons
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
