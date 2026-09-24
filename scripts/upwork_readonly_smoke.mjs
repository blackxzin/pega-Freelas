import { chromium } from '@playwright/test';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { getPlatform, getSelectors } from './selectors.mjs';
import { loadLocalEnv } from './local_env.mjs';
import { isAccessChallenge } from './access_guard.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
loadLocalEnv(`${root}/.env`);
const profileDir = process.env.BROWSER_PROFILE_DIR || `${root}/browser-profile`;
mkdirSync(profileDir, { recursive: true });
const platform = getPlatform('upwork');
const selectors = getSelectors('upwork');

async function main() {
  const context = await chromium.launchPersistentContext(profileDir, { headless: true });
  try {
    const page = context.pages()[0] || await context.newPage();
    const consoleErrors = [];
    page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text().slice(0, 160)); });
    await page.goto(platform.listing_url, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(2500);
    const challenge = await isAccessChallenge(page);
    const jobLinks = await page.locator("a[href*='/jobs/']").count();
    const listingHits = {};
    for (const [name, values] of Object.entries(selectors.listing)) {
      listingHits[name] = Math.max(...await Promise.all(values.map((selector) => page.locator(selector).count())));
    }
    const title = await page.title().catch(() => '');
    console.log(JSON.stringify({
      event: 'upwork_readonly_smoke',
      ok: !challenge,
      url: page.url(),
      title,
      access_challenge: challenge,
      job_links: jobLinks,
      listing_hits: listingHits,
      console_errors: consoleErrors.length,
    }));
  } finally {
    await context.close();
  }
}

main().catch((error) => {
  console.error(JSON.stringify({ event: 'upwork_readonly_smoke', ok: false, error: error.message }));
  process.exitCode = 1;
});
