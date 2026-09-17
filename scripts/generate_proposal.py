"""Generate one proposal/question from a job snapshot on stdin."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from freelahunter.core import ProfileService
from freelahunter.quoting import build_quote


def main() -> None:
    profile_path = Path(__file__).resolve().parents[1] / 'config/profile.yaml'
    print(json.dumps(build_quote(json.load(sys.stdin), ProfileService(str(profile_path)).load()), ensure_ascii=False))


if __name__ == '__main__':
    main()
