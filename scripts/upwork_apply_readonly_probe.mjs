import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { loadLocalEnv } from './local_env.mjs';
import { isAccessChallenge } from './access_guard.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
loadLocalEnv(`${root}/.env`);
const profileDir = process.env.BROWSER_PROFILE_DIR || `${root}/browser-profile`;
const target = process.env.TARGET_JOB_URL;
if (!target) throw new Error('TARGET_JOB_URL is required');
mkdirSync(profileDir, { recursive: true });

async function visibleTexts(page, selector) {
  const rows = [];
  const nodes = page.locator(selector);
  for (let index = 0; index < Math.min(await nodes.count(), 80); index += 1) {
    const node = nodes.nth(index);
    if (!await node.isVisible().catch(() => false)) continue;
    const text = (await node.innerText().catch(() => '')).replace(/\s+/g, ' ').trim();
    const aria = await node.getAttribute('aria-label').catch(() => '') || '';
    const name = await node.getAttribute('name').catch(() => '') || '';
    const type = await node.getAttribute('type').catch(() => '') || '';
    if (text || aria || name || type) rows.push({ text: text.slice(0, 160), aria, name, type });
  }
  return rows;
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
    console.log(JSON.stringify({
      event: 'upwork_apply_readonly_probe',
      url: page.url(),
      title: await page.title().catch(() => ''),
      access_challenge: await isAccessChallenge(page),
      links: (await visibleTexts(page, 'a')).filter((row) => /apply|proposal|connect|submit|offer|hire/i.test(`${row.text} ${row.aria}`)),
      buttons: (await visibleTexts(page, 'button')).filter((row) => /apply|proposal|connect|submit|offer|hire/i.test(`${row.text} ${row.aria}`)),
      fields: await visibleTexts(page, 'input, textarea, select'),
    }));
  } finally {
    await context.close();
  }
}

main().catch((error) => {
  console.error(JSON.stringify({ event: 'upwork_apply_readonly_probe', ok: false, error: error.message }));
  process.exitCode = 1;
});
