import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
export const selectors = JSON.parse(readFileSync(`${root}/config/selectors.json`, 'utf8'));

export async function firstLocator(page, candidates, { visible = false } = {}) {
  for (const selector of candidates) {
    const locator = page.locator(selector).first();
    if (await locator.count() && (!visible || await locator.isVisible().catch(() => false))) return locator;
  }
  return null;
}

export async function hasAny(page, candidates) {
  for (const selector of candidates) {
    if (await page.locator(selector).first().count()) return selector;
  }
  return null;
}
