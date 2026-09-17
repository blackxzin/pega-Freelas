"""Optional FastAPI surface. Core operation remains usable without web deps."""
from .core import Database, ProviderRegistry

def create_app(db=None, registry=None, admin_token=None):
    try:
        from fastapi import FastAPI, Header, HTTPException
    except ImportError:
        return None
    app=FastAPI(title='FreelaHunter AI'); database=db or Database(); providers=registry or ProviderRegistry(); token=admin_token
    def auth(x_admin_token):
        if token and x_admin_token!=token: raise HTTPException(401,'admin authentication required')
    @app.get('/system/status')
    def status(): return {'providers':[p.name for p in providers.enabled()]}
    @app.get('/providers')
    def get_providers(): return [{'name':p.name,'authorized_send':p.capabilities.authorized_send} for p in providers.enabled()]
    @app.get('/metrics')
    def metrics(): return {'status':'ok'}
    @app.post('/system/kill-switch')
    def kill_switch(enabled: bool=True, x_admin_token: str|None=Header(default=None)):
        auth(x_admin_token); return {'kill_switch':enabled}
    return app
