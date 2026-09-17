from freelahunter.core import *

def job(): return Job('API FastAPI', 'API REST Python FastAPI SQL', external_id='1', url='https://x/1', skills=['Python','FastAPI','SQL'], budget_min=500, budget_max=2000)

def test_authorized_autosend_is_idempotent():
    db=Database(':memory:'); sender=MockSender(); p=AuthorizedMockProvider([job()])
    first=run_pipeline(p,db,auto_send=True,dry_run=False,kill_switch=False,sender=sender)
    second=run_pipeline(p,db,auto_send=True,dry_run=False,kill_switch=False,sender=sender)
    assert first['sent']==1 and second['duplicates']==1 and len(sender.sent)==1

def test_safety_guards_block_send():
    for kwargs in ({'dry_run':True},{'auto_send':False},{'kill_switch':True}):
        sender=MockSender()
        opts={'auto_send':True,'dry_run':False,'kill_switch':False,'sender':sender}; opts.update(kwargs)
        db=Database(':memory:'); s=run_pipeline(AuthorizedMockProvider([job()]),db,**opts)
        assert s['sent']==0 and not sender.sent

def test_unauthorized_provider_never_sends():
    sender=MockSender(); s=run_pipeline(MockProvider([job()]),Database(':memory:'),auto_send=True,dry_run=False,kill_switch=False,sender=sender)
    assert s['sent']==0

def test_validator_blocks_placeholders():
    p=ProposalDraft(1,'x','TODO [CLIENT]',1,None,[])
    assert ProposalValidator().validate(p,Profile()) [0]=='FAILED'
