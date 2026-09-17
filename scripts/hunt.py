import argparse, os, sys
from pathlib import Path; sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from freelahunter.core import *

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--provider',default='mock'); args=ap.parse_args()
    reg=ProviderRegistry(); reg.register('mock',MockProvider()); reg.register('authorized_mock',AuthorizedMockProvider())
    provider=reg.get(args.provider); db=Database(os.getenv('DATABASE_PATH','freelahunter.db'))
    s=run_pipeline(provider,db,auto_send=os.getenv('AUTO_SEND','false').lower()=='true',dry_run=os.getenv('DRY_RUN','true').lower()=='true',kill_switch=os.getenv('AUTO_SEND_KILL_SWITCH','true').lower()=='true')
    print(s)
if __name__=='__main__': main()
