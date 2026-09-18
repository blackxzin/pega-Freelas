import json
import os
from urllib.request import Request, urlopen

from .core import NotificationService


class DiscordNotificationService(NotificationService):
    """Small optional notifier for worker-side pause/error events."""

    def notify(self, event, payload):
        webhook = os.getenv('DISCORD_WEBHOOK_URL')
        if not webhook:
            return {'event': event, 'delivered': False, 'reason': 'webhook ausente'}
        content = f'FreelaHunter {event}: {payload}'
        request = Request(webhook + ('&' if '?' in webhook else '?') + 'wait=true',
                          data=json.dumps({'content': content, 'allowed_mentions': {'parse': []}}).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urlopen(request, timeout=10) as response:
                return {'event': event, 'delivered': 200 <= response.status < 300}
        except Exception as exc:
            return {'event': event, 'delivered': False, 'reason': str(exc)}

class NullNotificationService(NotificationService): pass
__all__=['NotificationService','NullNotificationService','DiscordNotificationService']
