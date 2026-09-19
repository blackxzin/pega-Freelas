import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { loadLocalEnv } from './local_env.mjs';
import { createInterface } from 'node:readline/promises';
import { isAccessChallenge, selectUpworkGoogleAccount, waitForManualAccess } from './access_guard.mjs';
import { getSelectors } from './selectors.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
loadLocalEnv(`${root}/.env`);
const profileDir = process.env.BROWSER_PROFILE_DIR || `${root}/browser-profile`;
const target = 'https://www.upwork.com/freelancers/~0173a99e2479ab2b2e';
mkdirSync(profileDir, { recursive: true });

async function fields(page) {
  const rows = [];
  const nodes = page.locator('input, textarea, [contenteditable="true"]');
  for (let index = 0; index < Math.min(await nodes.count(), 100); index += 1) {
    const node = nodes.nth(index);
    if (!await node.isVisible().catch(() => false)) continue;
    rows.push({
      tag: await node.evaluate((element) => element.tagName).catch(() => ''),
      name: await node.getAttribute('name').catch(() => '') || '',
      type: await node.getAttribute('type').catch(() => '') || '',
      aria: await node.getAttribute('aria-label').catch(() => '') || '',
      placeholder: await node.getAttribute('placeholder').catch(() => '') || '',
      value_length: ((await node.inputValue().catch(() => '')) || (await node.innerText().catch(() => ''))).length,
    });
  }
  return rows;
}

async function texts(page, selector) {
  const result = [];
  const nodes = page.locator(selector);
  for (let index = 0; index < Math.min(await nodes.count(), 80); index += 1) {
    const node = nodes.nth(index);
    if (!await node.isVisible().catch(() => false)) continue;
    const text = (await node.innerText().catch(() => '')).replace(/\s+/g, ' ').trim();
    if (text) result.push(text.slice(0, 180));
  }
  return result;
}

async function main() {
  const context = await chromium.launchPersistentContext(profileDir, {
    headless: false,
    ignoreDefaultArgs: ['--enable-automation'],
    args: ['--disable-blink-features=AutomationControlled'],
  });
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(4000);
    const auth = getSelectors('upwork').auth;
    const selected = await selectUpworkGoogleAccount(page, auth, process.env.UPWORK_GOOGLE_ACCOUNT_LABEL || 'Lucas');
    if (selected || /accounts\.google\.com|account-security\/login|\/signup/i.test(page.url())) {
      const rl = createInterface({ input: process.stdin, output: process.stdout });
      await rl.question('Conclua o login/2FA no Chromium e pressione Enter aqui: ');
      rl.close();
      await waitForManualAccess(page, 'upwork', (question) => createInterface({ input: process.stdin, output: process.stdout }).question(question));
      await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 30000 });
      await page.waitForTimeout(4000);
    }
    console.log(JSON.stringify({
      event: 'upwork_profile_readonly_probe',
      url: page.url(),
      title: await page.title().catch(() => ''),
      access_challenge: await isAccessChallenge(page),
      fields: await fields(page),
      buttons: await texts(page, 'button'),
      links: await page.locator('a').evaluateAll((anchors) => anchors.slice(0, 120).map((anchor) => ({
        text: anchor.innerText.replace(/\s+/g, ' ').trim().slice(0, 120),
        href: anchor.href,
      })).filter((row) => row.text || row.href)),
    }));
  } finally {
    await context.close();
  }
}

main().catch((error) => {
  console.error(JSON.stringify({ event: 'upwork_profile_readonly_probe', ok: false, error: error.message }));
  process.exitCode = 1;
});
