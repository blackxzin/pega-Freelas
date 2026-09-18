import { chromium } from '@playwright/test';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { readSnapshot } from './job_snapshot.mjs';
import { selectors } from './selectors.mjs';
import { loadLocalEnv } from './local_env.mjs';

const root = fileURLToPath(new URL('..', import.meta.url));
loadLocalEnv(`${root}/.env`);
const profileDir = process.env.BROWSER_PROFILE_DIR || `${root}/browser-profile`;
const listingUrl = process.env.JOBS_URL || 'https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&page=4';

async function main() {
  const context = await chromium.launchPersistentContext(profileDir, { headless: true });
  try {
    const page = context.pages()[0] || await context.newPage();
    await page.goto(listingUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const link = page.locator(selectors.listing.links[0]).first();
    if (!await link.count()) throw new Error('nenhuma vaga encontrada na listagem real');
    await page.goto(new URL(await link.getAttribute('href'), page.url()).href, { waitUntil: 'domcontentloaded', timeout: 30000 });
    const snapshot = await readSnapshot(page);
    const generated = spawnSync('python', ['scripts/generate_proposal.py'], { cwd: root, input: JSON.stringify(snapshot), encoding: 'utf8' });
    if (generated.status !== 0) throw new Error(generated.stderr || 'geração falhou');
    const draft = JSON.parse(generated.stdout);
    await page.goto('https://www.99freelas.com.br/messages/inbox', { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(2500);
    let inboxRows = 0;
    for (const candidate of selectors.inbox.row) inboxRows = Math.max(inboxRows, await page.locator(candidate).count());
    console.log(JSON.stringify({ event: 'live_readonly_test', ok: true, title: snapshot.title, action: draft.action, price: draft.suggested_price ?? null, validation_status: draft.validation_status ?? null, inbox_rows: inboxRows }));
  } finally { await context.close(); }
}

main().catch((error) => { console.error(JSON.stringify({ event: 'live_readonly_test', ok: false, error: error.message })); process.exitCode = 1; });
