const WEBHOOK_PATH = /^\/api\/webhooks\/\d+\/[A-Za-z0-9._-]+$/;

export function validateDiscordWebhook(value) {
  let url;
  try { url = new URL(value); }
  catch { throw new Error('DISCORD_WEBHOOK_URL inválida.'); }
  if (url.protocol !== 'https:' || !['discord.com', 'www.discord.com', 'discordapp.com'].includes(url.hostname) ||
      !WEBHOOK_PATH.test(url.pathname) || url.search || url.hash) {
    throw new Error('DISCORD_WEBHOOK_URL inválida.');
  }
  return url.toString();
}

export async function sendDiscordNotification(webhookUrl, content, fetchImpl = fetch,
  sleepImpl = (ms) => new Promise((resolve) => setTimeout(resolve, ms))) {
  const target = validateDiscordWebhook(webhookUrl);
  if (!content || content.length > 2000) throw new Error('Conteúdo da notificação inválido.');
  const retryable = new Set([429, 500, 502, 503, 504]);
  for (let attempt = 0; attempt < 3; attempt += 1) {
    const response = await fetchImpl(`${target}?wait=true`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ content, allowed_mentions: { parse: [] } }),
    });
    if (response.ok) return response.status;
    if (!retryable.has(response.status) || attempt === 2) {
      throw new Error(`Discord recusou notificação (HTTP ${response.status}).`);
    }
    let retryAfter = Number(response.headers?.get?.('retry-after')) * 1000;
    if (!Number.isFinite(retryAfter) || retryAfter < 0) retryAfter = 500 * (2 ** attempt);
    await sleepImpl(Math.min(retryAfter, 10000));
  }
  throw new Error('Discord recusou notificação.');
}
