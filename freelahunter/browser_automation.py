"""Safe adapter for browser-based proposal review.

Platform selectors and credentials stay outside this package. This module never
attempts to bypass CAPTCHA, anti-bot controls, or a platform's terms of use.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlparse
import re

from .core import Job, ProposalDraft


class BrowserPage(Protocol):
    def open(self, url: str) -> None: ...
    def fill(self, selector: str, value: str) -> None: ...
    def click(self, selector: str) -> None: ...


class PlaywrightPageAdapter:
    """Adapt a synchronous Playwright page to the safe browser protocol."""

    def __init__(self, page):
        self.page = page

    def open(self, url: str) -> None:
        self.page.goto(url, wait_until='domcontentloaded')

    def fill(self, selector: str, value: str) -> None:
        self.page.locator(selector).fill(value)

    def click(self, selector: str) -> None:
        self.page.locator(selector).click()


class BrowserAutomationError(ValueError):
    """Raised before an unsafe browser action reaches a page."""


class PremiumFeatureError(BrowserAutomationError):
    """Raised when an action would require a paid platform feature."""


class BrowserActionPolicy:
    """Keep browser automation on free, public platform features only by default."""

    PREMIUM_MARKERS = ('premium', 'pro', 'assinar', 'assinatura', 'comprar', 'turbinar')

    def __init__(self, premium_features_enabled: bool = False):
        self.premium_features_enabled = premium_features_enabled

    def allow(self, action_label: str) -> None:
        normalized = action_label.casefold()
        if not self.premium_features_enabled and any(
            re.search(r'\b' + re.escape(marker) + r'\b', normalized) for marker in self.PREMIUM_MARKERS
        ):
            raise PremiumFeatureError('premium platform features are disabled')

    def project_is_eligible(self, project_text: str, *, has_gold_badge: bool = False) -> bool:
        if has_gold_badge and not self.premium_features_enabled:
            return False
        try:
            self.allow(project_text)
        except PremiumFeatureError:
            return False
        return True


@dataclass(frozen=True)
class ProposalFormSelectors:
    subject: str
    message: str
    submit: str


class ProposalBrowserAutomation:
    """Open and prefill a proposal; submit only with explicit approval."""

    def __init__(
        self,
        page: BrowserPage,
        selectors: ProposalFormSelectors,
        action_policy: BrowserActionPolicy | None = None,
    ):
        self.page = page
        self.selectors = selectors
        self.action_policy = action_policy or BrowserActionPolicy()

    @staticmethod
    def _validate_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != 'https' or not parsed.netloc:
            raise BrowserAutomationError('job URL must be an absolute HTTPS URL')

    def open_job(self, job: Job, *, has_gold_badge: bool = False) -> None:
        self._validate_url(job.url)
        if has_gold_badge and not self.action_policy.premium_features_enabled:
            raise PremiumFeatureError('gold badge projects are disabled')
        self.action_policy.allow(job.title)
        self.page.open(job.url)

    def prefill(self, proposal: ProposalDraft) -> None:
        if proposal.validation_status != 'PASSED':
            raise BrowserAutomationError('only validated proposals may be prefilled')
        self.page.fill(self.selectors.subject, proposal.subject)
        self.page.fill(self.selectors.message, proposal.message)

    def submit(self, *, explicit_user_approval: bool, authorized_provider: bool) -> None:
        self.action_policy.allow(self.selectors.submit)
        if not explicit_user_approval:
            raise BrowserAutomationError('explicit user approval is required to submit')
        if not authorized_provider:
            raise BrowserAutomationError('provider is not authorized for browser submission')
        self.page.click(self.selectors.submit)
