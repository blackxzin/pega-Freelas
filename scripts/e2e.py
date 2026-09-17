import sys; from pathlib import Path; sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from freelahunter.core import *
def main():
    jobs=[Job(f'API REST projeto {i}','Implementar API em Python FastAPI com SQL',external_id=str(i),url=f'https://mock/{i}',budget_min=500,budget_max=2000,skills=['Python','FastAPI','SQL']) for i in range(100)]
    db=Database(':memory:'); s=run_pipeline(AuthorizedMockProvider(jobs),db,auto_send=True,dry_run=False,kill_switch=False,sender=MockSender(),max_per_hour=100,max_per_day=100); print(f"Jobs: {s['found']}\nFiltered: {s['filtered']}\nAnalyzed: {s['analyzed']}\nProposals: {s['proposals']}\nAuto-send eligible: {s['sent']}\nSent: {s['sent']}\nDuplicates prevented: {s['duplicates']}\nErrors: {s['errors']}")
if __name__=='__main__': main()
