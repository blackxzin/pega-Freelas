import sys; from pathlib import Path; sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from freelahunter.core import *
def main():
    db=Database(':memory:'); p=AuthorizedMockProvider([Job('Dashboard React','Dashboard com React, TypeScript e JavaScript',external_id='demo',url='https://mock/demo',skills=['React','TypeScript','JavaScript'])]); sender=MockSender(); print(run_pipeline(p,db,auto_send=True,dry_run=False,kill_switch=False,sender=sender)); print(run_pipeline(p,db,auto_send=True,dry_run=False,kill_switch=False,sender=sender)); print('sender calls:',len(sender.sent))
if __name__=='__main__': main()
