import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { getSelectors } from './selectors.mjs';
import { loadLocalEnv } from './local_env.mjs';
import { isAccessChallenge } from './access_guard.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
loadLocalEnv(`${root}/.env`);
const profileDir = process.env.BROWSER_PROFILE_DIR || `${root}/browser-profile`;
const target = process.env.TARGET_JOB_URL;
if (!target) throw new Error('TARGET_JOB_URL is required');
mkdirSync(profileDir, { recursive: true });

async function probe(page, selectors) {
  const result = {};
  for (const [name, candidates] of Object.entries(selectors)) {
    result[name] = [];
    for (const selector of candidates) {
      const locator = page.locator(selector);
      const count = await locator.count();
      if (count) result[name].push({ selector, count, text: (await locator.first().innerText().catch(() => '')).slice(0, 180) });
    }
  }
  return result;
}

async function main() {
  const context = await chromium.launchPersistentContext(profileDir, { headless: true });
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(3500);
    const selectors = getSelectors('upwork');
    console.log(JSON.stringify({
      event: 'upwork_job_readonly_probe',
      url: page.url(),
      title: await page.title().catch(() => ''),
      access_challenge: await isAccessChallenge(page),
      job: await probe(page, selectors.job),
      proposal: await probe(page, selectors.proposal),
      h1: await page.locator('h1').allTextContents().catch(() => []),
    }));
  } finally {
    await context.close();
  }
}

main().catch((error) => {
  console.error(JSON.stringify({ event: 'upwork_job_readonly_probe', ok: false, error: error.message }));
  process.exitCode = 1;
});
