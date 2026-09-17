from .core import MockSender
class ProposalSender: pass
class AuthorizedApiSender(MockSender): pass
__all__=['ProposalSender','MockSender','AuthorizedApiSender']
