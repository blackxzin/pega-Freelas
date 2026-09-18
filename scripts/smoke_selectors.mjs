import { chromium } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { selectors } from './selectors.mjs';
import { loadLocalEnv } from './local_env.mjs';
import { sendDiscordNotification } from './discord_notify.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
loadLocalEnv(`${root}/.env`);
const profileDir = process.env.BROWSER_PROFILE_DIR || `${root}/browser-profile`;
const listingUrl = process.env.JOBS_URL || 'https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&page=4';
const jobUrl = process.env.SMOKE_JOB_URL;

async function check(page, name, candidates) {
  const found = [];
  for (const selector of candidates) {
    if (await page.locator(selector).count()) found.push(selector);
  }
  return { name, ok: found.length > 0, found, candidates };
}

async function main() {
  const context = await chromium.launchPersistentContext(profileDir, { headless: true });
  const results = [];
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.goto(listingUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    results.push(...await Promise.all(Object.entries(selectors.listing).map(([name, values]) => check(page, `listing.${name}`, values))));
    let resolvedJobUrl = jobUrl;
    if (!resolvedJobUrl) {
      const candidate = page.locator(selectors.listing.links[0]).first();
      if (await candidate.count()) resolvedJobUrl = await candidate.getAttribute('href');
    }
    if (resolvedJobUrl) {
      await page.goto(new URL(resolvedJobUrl, page.url()).href, { waitUntil: 'domcontentloaded', timeout: 30000 });
      for (const [name, values] of Object.entries(selectors.job)) results.push(await check(page, `job.${name}`, values));
      const bid = page.locator(selectors.proposal.bid_link[0]).first();
      const bidHref = await bid.count() ? await bid.getAttribute('href') : null;
      if (bidHref) {
        await page.goto(new URL(bidHref, page.url()).href, { waitUntil: 'domcontentloaded', timeout: 30000 });
        for (const [name, values] of Object.entries(selectors.proposal)) results.push(await check(page, `proposal.${name}`, values));
      }
    }
    await page.goto('https://www.99freelas.com.br/messages/inbox', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(2000);
    for (const [name, values] of Object.entries(selectors.inbox)) results.push(await check(page, `inbox.${name}`, values));
    const optional = new Set(['job.premium_badge', 'job.budget', 'job.deadline', 'proposal.bid_link', 'proposal.subject', 'proposal.question', 'proposal.submit_question', 'proposal.continue_modal', 'proposal.final_price', 'proposal.duration']);
    const broken = results.filter((row) => !row.ok && !optional.has(row.name));
    const warnings = results.filter((row) => !row.ok && optional.has(row.name));
    const output = { event: 'selector_smoke_test', timestamp: new Date().toISOString(), ok: broken.length === 0, checked: results.length, broken: broken.map((row) => row.name), warnings: warnings.map((row) => row.name) };
    console.log(JSON.stringify(output));
    if (broken.length && process.env.DISCORD_WEBHOOK_URL) await sendDiscordNotification(process.env.DISCORD_WEBHOOK_URL, `⚠️ Smoke test FreelaHunter: ${broken.length} seletor(es) quebrado(s): ${broken.map((row) => row.name).join(', ')}`);
    process.exitCode = broken.length ? 1 : 0;
  } finally { await context.close(); }
}

main().catch((error) => { console.error(JSON.stringify({ event: 'selector_smoke_error', error: error.message })); process.exitCode = 1; });
