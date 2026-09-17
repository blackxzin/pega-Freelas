import pytest

from freelahunter.browser_automation import (
    BrowserActionPolicy,
    BrowserAutomationError,
    PremiumFeatureError,
    PlaywrightPageAdapter,
    ProposalBrowserAutomation,
    ProposalFormSelectors,
)
from freelahunter.core import Job, ProposalDraft


class FakePage:
    def __init__(self):
        self.events = []

    def open(self, url): self.events.append(('open', url))
    def fill(self, selector, value): self.events.append(('fill', selector, value))
    def click(self, selector): self.events.append(('click', selector))


def proposal(status='PASSED'):
    return ProposalDraft(1, 'Proposta: API', 'palavra ' * 100, 10, 1000, [], validation_status=status)


def test_browser_flow_opens_https_job_and_prefills_validated_proposal():
    page = FakePage()
    flow = ProposalBrowserAutomation(page, ProposalFormSelectors('#subject', '#message', '#submit'))
    flow.open_job(Job('API', 'Criar API', url='https://example.test/jobs/1'))
    flow.prefill(proposal())
    assert page.events == [
        ('open', 'https://example.test/jobs/1'),
        ('fill', '#subject', 'Proposta: API'),
        ('fill', '#message', 'palavra ' * 100),
    ]


@pytest.mark.parametrize('url', ['', 'http://example.test/job', 'javascript:alert(1)'])
def test_browser_flow_rejects_non_https_job_urls(url):
    flow = ProposalBrowserAutomation(FakePage(), ProposalFormSelectors('#subject', '#message', '#submit'))
    with pytest.raises(BrowserAutomationError, match='HTTPS'):
        flow.open_job(Job('API', 'Criar API', url=url))


def test_browser_flow_never_submits_without_explicit_approval():
    page = FakePage()
    flow = ProposalBrowserAutomation(page, ProposalFormSelectors('#subject', '#message', '#submit'))
    with pytest.raises(BrowserAutomationError, match='approval'):
        flow.submit(explicit_user_approval=False, authorized_provider=True)
    assert page.events == []


def test_browser_flow_never_prefills_unvalidated_proposal():
    flow = ProposalBrowserAutomation(FakePage(), ProposalFormSelectors('#subject', '#message', '#submit'))
    with pytest.raises(BrowserAutomationError, match='validated'):
        flow.prefill(proposal('FAILED'))


def test_browser_policy_blocks_paid_features_and_premium_projects():
    policy = BrowserActionPolicy()
    assert policy.project_is_eligible('Integração de sistemas via API')
    assert not policy.project_is_eligible('Projeto exclusivo Premium')
    with pytest.raises(PremiumFeatureError, match='disabled'):
        policy.allow('Assinar plano Pro')


def test_browser_policy_blocks_gold_badge_projects_without_opening_them():
    page = FakePage()
    flow = ProposalBrowserAutomation(page, ProposalFormSelectors('#subject', '#message', '#submit'))

    assert not BrowserActionPolicy().project_is_eligible(
        'Integração de sistemas via API', has_gold_badge=True
    )
    with pytest.raises(PremiumFeatureError, match='gold badge'):
        flow.open_job(
            Job('Integração de sistemas via API', 'Criar integração', url='https://example.test/jobs/1'),
            has_gold_badge=True,
        )
    assert page.events == []


def test_playwright_adapter_maps_page_operations():
    class Locator:
        def __init__(self, events, selector):
            self.events, self.selector = events, selector

        def fill(self, value): self.events.append(('fill', self.selector, value))
        def click(self): self.events.append(('click', self.selector))

    class PlaywrightFake:
        def __init__(self): self.events = []
        def goto(self, url, wait_until): self.events.append(('goto', url, wait_until))
        def locator(self, selector): return Locator(self.events, selector)

    page = PlaywrightFake()
    adapter = PlaywrightPageAdapter(page)
    adapter.open('https://example.test/job')
    adapter.fill('#message', 'teste')
    adapter.click('#submit')

    assert page.events == [
        ('goto', 'https://example.test/job', 'domcontentloaded'),
        ('fill', '#message', 'teste'),
        ('click', '#submit'),
    ]
