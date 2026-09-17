"""Generate one proposal/question from a job snapshot on stdin."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from freelahunter.core import AIService, Job, PortfolioService, PriceEstimator, ProfileService, ProposalGenerator


def main() -> None:
    payload = json.load(sys.stdin)
    job = Job(
        title=payload.get('title', 'Projeto de desenvolvimento'),
        description=payload.get('description', ''),
        url=payload.get('url', ''),
        budget_max=payload.get('budget_max'),
    )
    profile = ProfileService().load()
    projects = PortfolioService().relevant(job, profile)
    analysis = AIService().analyze(job, profile, projects)
    price, _ = PriceEstimator(
        hourly_rate=100,
        minimum_project_price=profile.minimum_budget or 500,
    ).estimate(
        (analysis.estimated_hours_min + analysis.estimated_hours_max) // 2,
        budget_max=job.budget_max,
    )
    proposal = ProposalGenerator().generate(job, analysis, profile, projects, price)
    print(json.dumps({
        'subject': proposal.subject,
        'message': proposal.message,
        'suggested_price': proposal.suggested_price,
        'estimated_hours': proposal.estimated_hours,
        'estimated_days': max(1, math.ceil(proposal.estimated_hours / 8)),
        'question': 'Quais integrações, prazo, orçamento e critérios de aceite são prioritários para esta etapa?',
    }, ensure_ascii=False))


if __name__ == '__main__':
    main()
