import os, time, sys
from pathlib import Path; sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from freelahunter.core import *
from freelahunter.scheduler import HunterScheduler
def main():
    dry=os.getenv('DRY_RUN','true').lower()=='true'; auto=os.getenv('AUTO_SEND','false').lower()=='true'; kill=os.getenv('AUTO_SEND_KILL_SWITCH','true').lower()=='true'; print('==================================================\nFREELAHUNTER AI WORKER\n=================================================='); print(f'DRY RUN: {dry}\nAUTO SEND: {auto}\nKILL SWITCH: {kill}\n'); db=Database(); reg=ProviderRegistry(); reg.register('mock',MockProvider()); reg.register('authorized_mock',AuthorizedMockProvider()); run=1
    scheduler=HunterScheduler(reg,db,Config())
    while True:
        print(f'Cycle #{run}'); print(scheduler.run_cycle()); run+=1
        if os.getenv('WORKER_ONCE','false').lower()=='true': break
        time.sleep(int(os.getenv('HUNT_INTERVAL_MINUTES','15'))*60)
if __name__=='__main__': main()
