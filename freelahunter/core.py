from __future__ import annotations
import hashlib, json, os, re, sqlite3, threading, uuid, time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol

def now(): return datetime.now(timezone.utc).isoformat()
def sha(value: str): return hashlib.sha256(value.encode()).hexdigest()

class JobStatus(str, Enum):
    NEW='NEW'; FILTERED='FILTERED'; ANALYZING='ANALYZING'; ANALYZED='ANALYZED'; REJECTED='REJECTED'; PROPOSAL_GENERATING='PROPOSAL_GENERATING'; PROPOSAL_GENERATED='PROPOSAL_GENERATED'; REVIEW_REQUIRED='REVIEW_REQUIRED'; APPROVED='APPROVED'; READY_TO_SEND='READY_TO_SEND'; SENDING='SENDING'; SENT='SENT'; SEND_FAILED='SEND_FAILED'; CLIENT_REPLIED='CLIENT_REPLIED'; ARCHIVED='ARCHIVED'; ERROR='ERROR'

@dataclass
class Job:
    title: str; description: str; platform: str='mock'; external_id: str=''; url: str=''; budget_min: float|None=None; budget_max: float|None=None; currency: str='BRL'; skills: list[str]=field(default_factory=list); category: str=''; client: str=''; published_at: str|None=None; id: int|None=None; status: JobStatus=JobStatus.NEW; content_hash: str=''; first_seen_at: str|None=None; last_seen_at: str|None=None
    def canonical(self): return self.url.lower().split('#')[0].rstrip('/') if self.url else f'{self.platform}:{self.external_id}'
    def compute_hash(self):
        title=' '.join(self.title.lower().split()); desc=' '.join(self.description.lower().split()); budget=f'{self.budget_min}:{self.budget_max}'
        self.content_hash=sha(title+desc+budget); return self.content_hash

@dataclass
class Profile:
    name: str=''; headline: str=''; bio: str=''; skills: list[str]=field(default_factory=list); experience: list[str]=field(default_factory=list); education: str=''; portfolio: list[str]=field(default_factory=list); preferred_jobs: list[str]=field(default_factory=list); excluded_jobs: list[str]=field(default_factory=list); minimum_budget: float|None=None; languages: list[str]=field(default_factory=list); team_description: str='equipe de desenvolvedores full stack'; client_pays_paid_services: bool=True; id: str='default'

@dataclass
class PortfolioProject:
    name: str; description: str; technologies: list[str]=field(default_factory=list); category: str=''; keywords: list[str]=field(default_factory=list); repository_url: str=''; demo_url: str=''

@dataclass
class Analysis:
    score: int; recommended: bool; difficulty: str; matched_skills: list[str]; missing_skills: list[str]; requirements: list[str]; risks: list[str]; relevant_projects: list[str]; estimated_hours_min: int; estimated_hours_max: int; confidence: float; reason: str

@dataclass
class ProposalDraft:
    job_id: int; subject: str; message: str; estimated_hours: int; suggested_price: float|None; questions: list[str]; generated_at: str=field(default_factory=now); generation_model: str='mock'; validation_status: str='PENDING'; id: int|None=None

class ProviderCapabilities:
    def __init__(self, search=True, details=True, authorized_send=False, status_tracking=False): self.search=search; self.details=details; self.authorized_send=authorized_send; self.status_tracking=status_tracking

class JobProvider(Protocol):
    name: str; capabilities: ProviderCapabilities
    def search(self) -> list[Job]: ...

class MockProvider:
    name='mock'; capabilities=ProviderCapabilities()
    def __init__(self, jobs=None): self.jobs=jobs or [Job(title='API REST em FastAPI', description='Criar API REST com Python FastAPI e SQL', external_id='mock-1', url='https://mock/jobs/1', budget_min=800, budget_max=1500, skills=['Python','FastAPI','SQL'])]
    def search(self): return self.jobs

class AuthorizedMockProvider(MockProvider):
    name='authorized_mock'; capabilities=ProviderCapabilities(authorized_send=True, status_tracking=True)

class ProviderRegistry:
    def __init__(self): self._providers={}
    def register(self, name, provider): self._providers[name]=provider
    def get(self, name): return self._providers[name]
    def enabled(self): return list(self._providers.values())

class ProfileService:
    def __init__(self, path='config/profile.yaml'): self.path=path
    def load(self):
        p=Profile(name='FreelaHunter User', headline='Desenvolvedor Full Stack | Python, APIs e Automação', skills=['Python','Java','JavaScript','TypeScript','HTML','CSS','React','Next.js','FastAPI','APIs REST','SQL','Linux','Git','GitHub','Automação','Integrações','IA'])
        if os.path.exists(self.path):
            import yaml
            data=yaml.safe_load(open(self.path)) or {}; 
            for k,v in data.items():
                if hasattr(p,k): setattr(p,k,v)
        return p

class PortfolioService:
    def __init__(self, projects=None): self.projects=projects or [PortfolioProject('API FastAPI', 'API REST para automação e integrações', ['Python','FastAPI','SQL'], 'backend', ['api','rest','automação'])]
    def relevant(self, job, profile):
        terms={x.lower() for x in job.skills + re.findall(r'[A-Za-z]+',job.title+' '+job.description)}
        return [p for p in self.projects if terms & {x.lower() for x in p.technologies+p.keywords}]

class FilterService:
    def __init__(self, included_keywords=None, excluded_keywords=None, minimum_budget=None, maximum_budget=None): self.included=set(x.lower() for x in (included_keywords or [])); self.excluded=set(x.lower() for x in (excluded_keywords or [])); self.minimum_budget=minimum_budget; self.maximum_budget=maximum_budget
    def accepts(self, job):
        text=(job.title+' '+job.description+' '+' '.join(job.skills)).lower()
        if self.excluded and any(x in text for x in self.excluded): return False
        if self.included and not any(x in text for x in self.included): return False
        if self.minimum_budget is not None and (job.budget_max or 0)<self.minimum_budget: return False
        if self.maximum_budget is not None and (job.budget_min or 0)>self.maximum_budget: return False
        return True

class AIService:
    def analyze(self, job, profile, projects):
        ps={x.lower() for x in profile.skills}; js={x.lower() for x in job.skills}; matched=sorted(js & ps); missing=sorted(js-ps); score=max(0,min(100, 50+len(matched)*15-len(missing)*8)); hours=max(4, len(job.skills)*3)
        return Analysis(score, score>=60, 'hard' if len(job.skills)>5 else 'medium', matched, missing, job.skills, [], [p.name for p in projects], hours, hours+7, .85, f'{len(matched)} competências compatíveis; escopo requer validação.')

class ProposalGenerator:
    def generate(self, job, analysis, profile, projects, price=None):
        tech=', '.join(analysis.matched_skills) or ', '.join(profile.skills[:3]); project=projects[0].name if projects else 'experiência com projetos de automação'
        msg=f'Olá! Eu e minha {profile.team_description} temos interesse em {job.title.lower()}. O objetivo é entregar uma solução funcional, documentada e fácil de manter. Podemos abordar o escopo com {tech}, organizando implementação em etapas, validando requisitos e deixando testes para fluxos críticos. Temos experiência comprovável em {project}, além de Git, APIs e comunicação clara. Primeiro confirmamos fluxo principal, entradas, saídas e critérios de aceite; depois definimos tarefas curtas para reduzir riscos e validar cada etapa. Para estimar com precisão: quais integrações, ambiente de hospedagem e critérios de aceite são prioritários?'
        if profile.client_pays_paid_services:
            msg += ' Custos de APIs, hospedagem, domínio, mensagens e créditos ficam nas contas do cliente; nossa proposta cobre desenvolvimento e configuração.'
        return ProposalDraft(job.id or 0, f'Proposta: {job.title}', msg, (analysis.estimated_hours_min+analysis.estimated_hours_max)//2, price, ['Quais são os critérios de aceite?'])

class ProposalValidator:
    BAD=['[CLIENT]','[PROJECT]','TODO','INSERT HERE','{{name}}']
    def validate(self, proposal, profile):
        m=proposal.message.strip(); low=m.lower(); reasons=[]
        if not 100 <= len(m.split()) <= 220: reasons.append('tamanho fora de 100-220 palavras')
        if not m or not proposal.subject: reasons.append('campo vazio')
        if any(x.lower() in low for x in self.BAD): reasons.append('placeholder')
        known={x.lower() for x in profile.skills}; mentioned=re.findall(r'\b[A-Za-z][A-Za-z+#.]+\b',m)
        # only flag obvious unsupported technology claims
        if any(t in low for t in ['django','kubernetes']) and not any(t in known for t in ['django','kubernetes']): reasons.append('tecnologia não presente no perfil')
        proposal.validation_status='PASSED' if not reasons else 'FAILED'; return proposal.validation_status, reasons

class PriceEstimator:
    def __init__(self, hourly_rate=None, minimum_project_price=None, preferred_project_price=None, currency='BRL'): self.hourly_rate=hourly_rate; self.minimum=minimum_project_price; self.preferred=preferred_project_price; self.currency=currency
    def estimate(self, hours, complexity='medium', budget_max=None):
        if self.hourly_rate is None and self.minimum is None and budget_max is None: return None, 'informações insuficientes'
        value=(hours*self.hourly_rate if self.hourly_rate else self.preferred or self.minimum or budget_max)
        if self.minimum: value=max(value,self.minimum)
        if budget_max: value=min(value,budget_max)
        return round(value,2), 'estimativa baseada em horas, taxa e orçamento anunciado'

class MockSender:
    def __init__(self): self.sent=[]
    def validate_credentials(self): return True
    def can_send(self): return True
    def send(self, proposal): self.sent.append(proposal); return {'external_id':str(uuid.uuid4()),'status':'SENT'}
    def get_status(self, external_id): return 'SENT'

class PipelineError(Exception):
    """Raised when a job cannot complete a safe pipeline stage."""

class NotificationService:
    def notify(self, event, payload):
        return {'event': event, 'payload': payload, 'delivered': False}

class CircuitBreaker:
    def __init__(self, failures=3, cooldown_seconds=1800): self.failures=failures; self.cooldown=cooldown_seconds; self._state={}
    def allow(self, provider):
        row=self._state.get(provider); return not row or row[1] <= time.time()
    def record_success(self, provider): self._state.pop(provider,None)
    def record_failure(self, provider, status=None):
        count, until=self._state.get(provider,(0,0)); count += 1
        self._state[provider]=(count, time.time()+self.cooldown if count>=self.failures else 0)

class Config:
    def __init__(self, environ=None):
        e=environ or os.environ
        def b(k,d): return e.get(k,d).lower() in ('1','true','yes','on')
        self.dry_run=b('DRY_RUN','true'); self.auto_send=b('AUTO_SEND','false'); self.kill_switch=b('AUTO_SEND_KILL_SWITCH','true'); self.automation_mode=e.get('AUTOMATION_MODE','SEMI_AUTO'); self.interval=int(e.get('HUNT_INTERVAL_MINUTES','15')); self.min_score=int(e.get('AUTO_SEND_MIN_SCORE','85')); self.min_confidence=float(e.get('MIN_CONFIDENCE','0.75')); self.max_hour=int(e.get('MAX_PROPOSALS_PER_HOUR','3')); self.max_day=int(e.get('MAX_PROPOSALS_PER_DAY','10'))
    def warnings(self):
        out=[]
        if self.automation_mode=='AUTO' and self.dry_run: out.append('AUTO MODE configured but DRY_RUN prevents external sending.')
        if self.auto_send and self.kill_switch: out.append('AUTO SEND disabled by kill switch.')
        return out

class SendPolicyEngine:
    def __init__(self, auto_send=False, dry_run=True, kill_switch=True, min_score=85, min_confidence=.75): self.auto_send=auto_send; self.dry_run=dry_run; self.kill_switch=kill_switch; self.min_score=min_score; self.min_confidence=min_confidence
    def decide(self, provider, analysis, proposal, sender, already_sent=False, within_limits=True):
        if already_sent: return 'BLOCKED'
        if not provider.capabilities.authorized_send or not self.auto_send or self.dry_run or self.kill_switch: return 'REVIEW_REQUIRED'
        if analysis.score<self.min_score or analysis.confidence<self.min_confidence or proposal.validation_status!='PASSED' or not within_limits or not sender.validate_credentials() or not sender.can_send(): return 'REVIEW_REQUIRED'
        return 'AUTO_SEND'

class Database:
    def __init__(self, path='freelahunter.db'):
        self.conn=sqlite3.connect(path, check_same_thread=False); self.lock=threading.Lock(); self.conn.execute('''CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, provider TEXT, external_id TEXT, canonical_url TEXT, title TEXT, description TEXT, budget_min REAL, budget_max REAL, currency TEXT, skills TEXT, status TEXT, content_hash TEXT, first_seen_at TEXT, last_seen_at TEXT, UNIQUE(provider,external_id))'''); self.conn.execute('''CREATE TABLE IF NOT EXISTS proposals (id INTEGER PRIMARY KEY, job_id INTEGER, idempotency_key TEXT UNIQUE, subject TEXT, message TEXT, validation_status TEXT, status TEXT, suggested_price REAL, sent_external_id TEXT)'''); self.conn.execute('''CREATE TABLE IF NOT EXISTS limits (bucket TEXT PRIMARY KEY, count INTEGER, reset_at TEXT)'''); self.conn.execute('''CREATE TABLE IF NOT EXISTS activity_logs (id INTEGER PRIMARY KEY, event TEXT, run_id TEXT, job_id INTEGER, created_at TEXT, details TEXT)'''); self.conn.execute('''CREATE TABLE IF NOT EXISTS limit_events (id INTEGER PRIMARY KEY, bucket TEXT, created_at REAL)'''); self.conn.commit()
    def upsert_job(self,j):
        j.compute_hash(); t=now()
        with self.lock:
            row=self.conn.execute('SELECT id,content_hash FROM jobs WHERE provider=? AND external_id=?',(j.platform,j.external_id)).fetchone()
            if row: j.id=row[0]; self.conn.execute('UPDATE jobs SET last_seen_at=?,content_hash=?,description=?,title=? WHERE id=?',(t,j.content_hash,j.description,j.title,j.id)); self.conn.commit(); return j, row[1]==j.content_hash
            cur=self.conn.execute('INSERT INTO jobs(provider,external_id,canonical_url,title,description,budget_min,budget_max,currency,skills,status,content_hash,first_seen_at,last_seen_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(j.platform,j.external_id,j.canonical(),j.title,j.description,j.budget_min,j.budget_max,j.currency,json.dumps(j.skills),j.status.value,j.content_hash,t,t)); j.id=cur.lastrowid; self.conn.commit(); return j,False
    def already_sent(self,key): return self.conn.execute('SELECT 1 FROM proposals WHERE idempotency_key=? AND status="SENT"',(key,)).fetchone() is not None
    def save_proposal(self,p,key,status='GENERATED'):
        self.conn.execute('INSERT OR REPLACE INTO proposals(job_id,idempotency_key,subject,message,validation_status,status,suggested_price) VALUES(?,?,?,?,?,?,?)',(p.job_id,key,p.subject,p.message,p.validation_status,status,p.suggested_price)); self.conn.commit()
    def mark_sent(self,key,external_id): self.conn.execute('UPDATE proposals SET status="SENT",sent_external_id=? WHERE idempotency_key=?',(external_id,key)); self.conn.commit()
    def within_limit(self, bucket, maximum, window_seconds=None):
        if maximum < 1: return False
        if window_seconds is None:
            row=self.conn.execute('SELECT count FROM limits WHERE bucket=?',(bucket,)).fetchone()
            return not row or row[0] < maximum
        cutoff=time.time()-window_seconds
        with self.lock:
            self.conn.execute('DELETE FROM limit_events WHERE bucket=? AND created_at<?',(bucket,cutoff))
            row=self.conn.execute('SELECT COUNT(*) FROM limit_events WHERE bucket=?',(bucket,)).fetchone()
            self.conn.commit()
        return row[0] < maximum
    def consume_limit(self, bucket):
        with self.lock:
            self.conn.execute('INSERT INTO limits(bucket,count,reset_at) VALUES(?,?,?) ON CONFLICT(bucket) DO UPDATE SET count=count+1',(bucket,1,now()))
            self.conn.execute('INSERT INTO limit_events(bucket,created_at) VALUES(?,?)',(bucket,time.time()))
            self.conn.commit()
    def audit(self,event,run_id=None,job_id=None,details=None):
        self.conn.execute('INSERT INTO activity_logs(event,run_id,job_id,created_at,details) VALUES(?,?,?,?,?)',(event,run_id,job_id,now(),json.dumps(details or {}))); self.conn.commit()

def run_pipeline(provider, db, profile=None, auto_send=False, dry_run=True, kill_switch=True,
                 sender=None, min_score=85, min_confidence=.75, max_per_hour=3,
                 max_per_day=10):
    """Discover jobs and prepare proposals. Sending needs every policy gate to pass."""
    profile=profile or ProfileService().load(); portfolio=PortfolioService(); ai=AIService(); gen=ProposalGenerator(); val=ProposalValidator(); sender=sender or MockSender(); policy=SendPolicyEngine(auto_send,dry_run,kill_switch,min_score,min_confidence); stats={'found':0,'new':0,'duplicates':0,'filtered':0,'analyzed':0,'proposals':0,'review':0,'sent':0,'errors':0}
    for job in provider.search():
        stats['found']+=1
        try:
            job.platform=provider.name; job,dup=db.upsert_job(job)
            if dup: stats['duplicates']+=1; continue
            stats['new']+=1
            if not FilterService().accepts(job): job.status=JobStatus.REJECTED; continue
            stats['filtered']+=1; projects=portfolio.relevant(job,profile); analysis=ai.analyze(job,profile,projects); stats['analyzed']+=1; price,_=PriceEstimator(hourly_rate=100,minimum_project_price=200).estimate((analysis.estimated_hours_min+analysis.estimated_hours_max)//2, budget_max=job.budget_max); p=gen.generate(job,analysis,profile,projects,price); val.validate(p,profile); stats['proposals']+=1; key=sha(provider.name+job.external_id+profile.id)
            within_limits=(db.within_limit('send-hour',max_per_hour,3600) and db.within_limit('send-day',max_per_day,86400))
            decision=policy.decide(provider,analysis,p,sender,db.already_sent(key),within_limits)
            db.save_proposal(p,key,'READY_TO_SEND' if decision=='AUTO_SEND' else 'REVIEW_REQUIRED')
            if decision=='AUTO_SEND':
                receipt=sender.send(p)
                external_id=receipt.get('external_id')
                if not external_id: raise PipelineError('sender returned no external_id')
                db.mark_sent(key,external_id); db.consume_limit('send-hour'); db.consume_limit('send-day'); stats['sent']+=1
            else: stats['review']+=1
        except Exception as exc:
            stats['errors']+=1
            db.audit('JOB_PIPELINE_ERROR',job_id=job.id,details={'provider':provider.name,'error':str(exc)})
    return stats
