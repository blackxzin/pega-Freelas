import { chromium } from '@playwright/test';
import { createInterface } from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import { spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const rl = createInterface({ input, output });
const ask = (question) => rl.question(question);
const root = fileURLToPath(new URL('..', import.meta.url));
const profileDir = process.env.BROWSER_PROFILE_DIR || `${root}/browser-profile`;
mkdirSync(profileDir, { recursive: true });
const maxJobs = Number(process.env.MAX_JOBS || 5);
const listingUrl = process.env.JOBS_URL || 'https://www.99freelas.com.br/projects?categoria=web-mobile-e-software';
const premium = /premium|projeto exclusivo|bandeira dourada|selo dourado|assinar|assinatura|turbinar/i;

function generate(snapshot) {
  const result = spawnSync('python', ['scripts/generate_proposal.py'], {
    cwd: root,
    input: JSON.stringify(snapshot),
    encoding: 'utf8',
  });
  if (result.status !== 0) throw new Error(result.stderr || 'falha ao gerar proposta');
  return JSON.parse(result.stdout);
}

async function visibleLocator(page, selectors) {
  for (const selector of selectors) {
    const locator = page.locator(selector).first();
    if (await locator.count() && await locator.isVisible().catch(() => false)) return locator;
  }
  return null;
}

async function fillJob(page, link) {
  await page.goto(link, { waitUntil: 'domcontentloaded', timeout: 30000 });
  const text = await page.locator('body').innerText();
  if (premium.test(text)) return { skipped: 'premium marker' };
  const title = await page.locator('h1').first().textContent().catch(() => null) || await page.title();
  const draft = generate({ title: title.trim(), description: text, url: page.url() });
  const proposalBox = await visibleLocator(page, ['#proposta', 'textarea[name*="proposta"]', 'textarea#message']);
  if (proposalBox) {
    const subject = await visibleLocator(page, ['#assunto', '#subject', 'input[name*="assunto"]']);
    const price = await visibleLocator(page, ['#oferta', 'input[name*="oferta"]']);
    const finalPrice = await visibleLocator(page, ['#oferta-final', 'input[name*="oferta-final"]']);
    const duration = await visibleLocator(page, ['#duracao-estimada', 'input[name*="duracao"]']);
    if (subject) await subject.fill(draft.subject);
    await proposalBox.fill(draft.message);
    if (price && draft.suggested_price != null) await price.fill(String(draft.suggested_price));
    if (duration) await duration.fill(String(draft.estimated_days));
    if (finalPrice && draft.suggested_price != null) await finalPrice.blur();
    return { kind: 'proposal', draft };
  }
  const question = await visibleLocator(page, ['#mensagem-pergunta', 'textarea[name*="pergunta"]']);
  if (question) {
    await question.fill(draft.question);
    return { kind: 'question', draft };
  }
  return { skipped: 'form not found' };
}

async function main() {
  let context;
  try {
    context = await chromium.launchPersistentContext(profileDir, { headless: false });
    const page = context.pages()[0] || await context.newPage();
    await page.goto(listingUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await ask('Faça login manualmente no Chromium. Quando terminar, pressione Enter aqui: ');
    const links = await page.locator('a[href]').evaluateAll((anchors) => {
    const seen = new Set();
    return anchors.map((anchor) => ({ href: anchor.href, text: anchor.innerText })).filter(({ href, text }) => {
      if (!/\/project(?:s)?\//i.test(href) || !text.trim() || seen.has(href)) return false;
      seen.add(href); return true;
    });
    });
    let processed = 0;
    for (const item of links) {
    if (processed >= maxJobs) break;
    if (premium.test(item.text)) continue;
    const result = await fillJob(page, item.href);
    if (result.skipped) { console.log(`IGNORADA: ${result.skipped} — ${item.href}`); continue; }
    processed += 1;
    console.log(`${result.kind.toUpperCase()} preenchida: ${result.draft.subject || item.href}`);
    console.log(`Valor sugerido: R$ ${result.draft.suggested_price ?? 'a combinar'} | prazo: ${result.draft.estimated_days} dias`);
    const answer = await ask('Digite ENVIAR para clicar no envio desta vaga, ou Enter para deixar como rascunho: ');
    if (answer.trim() === 'ENVIAR') {
      const submit = await visibleLocator(page, ['#enviar-proposta', 'button:has-text("Enviar proposta")', 'button:has-text("Enviar pergunta")', 'input[type="submit"]']);
      if (submit) { await submit.click(); console.log('ENVIO CLICADO pelo usuário.'); }
      else console.log('Botão de envio não localizado; rascunho preservado.');
    }
    }
    console.log(`Concluído: ${processed} vaga(s). Chromium permanece aberto para revisão.`);
    await ask('Pressione Enter para fechar Chromium: ');
  } finally {
    if (context) await context.close();
    rl.close();
  }
}

main().catch((error) => { console.error(error.message); rl.close(); process.exitCode = 1; });
