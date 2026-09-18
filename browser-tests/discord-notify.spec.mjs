import { expect, test } from '@playwright/test';
import { sendDiscordNotification, validateDiscordWebhook } from '../scripts/discord_notify.mjs';
import { formatDiscordAlert, incomingConversations, messageKey } from '../scripts/monitor_inbox.mjs';

const webhook = 'https://discord.com/api/webhooks/123456789012345678/example_token';

test('webhook Discord aceita somente URL HTTPS válida', () => {
  expect(validateDiscordWebhook(webhook)).toBe(webhook);
  expect(() => validateDiscordWebhook('https://example.com/api/webhooks/1/token')).toThrow('inválida');
  expect(() => validateDiscordWebhook('http://discord.com/api/webhooks/1/token')).toThrow('inválida');
});

test('notificação Discord bloqueia menções e confirma entrega', async () => {
  let request;
  const status = await sendDiscordNotification(webhook, 'Alerta @everyone', async (url, options) => {
    request = { url, options };
    return { ok: true, status: 200 };
  });
  expect(status).toBe(200);
  expect(request.url).toContain('?wait=true');
  expect(JSON.parse(request.options.body).allowed_mentions).toEqual({ parse: [] });
});

test('notificação repete falha transitória', async () => {
  let calls = 0;
  const status = await sendDiscordNotification(webhook, 'Alerta', async () => {
    calls += 1;
    return calls < 2 ? { ok: false, status: 503 } : { ok: true, status: 204 };
  }, async () => {});
  expect(status).toBe(204);
  expect(calls).toBe(2);
});

test('monitor avisa somente resposta nova do cliente', () => {
  const base = { id: '42', timestamp: '10', project: 'Site', client: 'Ana', preview: 'Olá', url: 'https://www.99freelas.com.br/messages/inbox/42' };
  const result = incomingConversations([
    { ...base, unread: true, sentByMe: false },
    { ...base, id: '43', unread: false, sentByMe: false },
    { ...base, id: '44', unread: true, sentByMe: true },
  ]);
  expect(result).toHaveLength(1);
  expect(formatDiscordAlert(result[0])).toContain('Abrir conversa: https://www.99freelas.com.br/messages/inbox/42');
});

test('conversa já registrada não gera alerta após reiniciar monitor', () => {
  const conversation = {
    id: '42', timestamp: '10', project: 'Site', client: 'Ana', preview: 'Olá',
    unread: true, sentByMe: false, url: 'https://www.99freelas.com.br/messages/inbox/42',
  };
  const firstScan = incomingConversations([conversation]);
  expect(firstScan).toHaveLength(1);
  // O estado persistido é testado pela mesma chave usada pelo monitor em produção.
  expect(incomingConversations([conversation], { [messageKey(conversation)]: Date.now() })).toHaveLength(0);
});
