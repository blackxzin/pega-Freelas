import { chromium } from '@playwright/test';
import { createInterface } from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import { spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { readSnapshot } from './job_snapshot.mjs';
import { hasExactMessage, hasPriorProjectIntroduction } from './submission_guard.mjs';

const rl = createInterface({ input, output });
const ask = (question) => rl.question(question);
const root = fileURLToPath(new URL('..', import.meta.url));
const profileDir = process.env.BROWSER_PROFILE_DIR || `${root}/browser-profile`;
mkdirSync(profileDir, { recursive: true });
const maxJobs = Number(process.env.MAX_JOBS || 5);
const listingUrl = process.env.JOBS_URL || 'https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&page=4';
const targetJobUrl = process.env.TARGET_JOB_URL;
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

async function conversationMessages(page, messagePageUrl) {
  await page.goto(messagePageUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  const conversationLink = page.locator('a[href*="/messages/"]:has-text("Ver conversa")').first();
  if (!await conversationLink.count()) return null;
  const href = await conversationLink.getAttribute('href');
  await page.goto(new URL(href, page.url()).href, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.waitForTimeout(500);
  return page.locator('.message-text').allTextContents();
}

async function alreadyContacted(page, messagePageUrl, draft) {
  const verifier = await page.context().newPage();
  try {
    const messages = await conversationMessages(verifier, messagePageUrl);
    if (!messages) return false;
    const title = draft.subject.replace(/^Proposta:\s*/i, '');
    return hasExactMessage(messages, draft.question) || hasPriorProjectIntroduction(messages, title);
  } finally {
    await verifier.close();
  }
}

async function verifyQuestion(page, messagePageUrl, expected) {
  const messages = await conversationMessages(page, messagePageUrl);
  return messages !== null && hasExactMessage(messages, expected);
}

async function fillJob(page, link) {
  await page.goto(link, { waitUntil: 'domcontentloaded', timeout: 30000 });
  let snapshot;
  try { snapshot = await readSnapshot(page); }
  catch (error) { return { skipped: error.message }; }
  const draft = generate(snapshot);
  if (draft.action === 'skip') return { skipped: draft.reason };
  console.log(JSON.stringify({ tasks: draft.breakdown, price_range: draft.price_range,
    client_total_range: draft.client_total_range, days_range: draft.days_range,
    questions: draft.questions }, null, 2));
  if (draft.action === 'question') {
    const questionLink = page.locator('a[href*="/project/message/"]').first();
    if (await questionLink.count()) {
      const href = await questionLink.getAttribute('href');
      await page.goto(new URL(href, page.url()).href, { waitUntil: 'domcontentloaded' });
    }
    const messagePageUrl = page.url();
    if (await alreadyContacted(page, messagePageUrl, draft)) {
      return { skipped: 'Conversa inicial desta vaga já existe; novo envio bloqueado para evitar duplicata.' };
    }
    const question = await visibleLocator(page, ['#mensagem-pergunta', 'textarea[name*="pergunta"]']);
    if (!question) {
      console.log(draft.question);
      return { skipped: 'Escopo exige esclarecimento; formulário de pergunta não localizado.' };
    }
    await question.fill(draft.question);
    return { kind: 'question', draft, messagePageUrl };
  }
  const bidLink = page.locator('a[href*="/project/bid/"]').first();
  if (!await bidLink.count()) {
    return { skipped: 'Candidatura indisponível ou proposta já existente; envio bloqueado para evitar duplicata.' };
  }
  const href = await bidLink.getAttribute('href');
  await page.goto(new URL(href, page.url()).href, { waitUntil: 'domcontentloaded' });
  const proposalBox = await visibleLocator(page, ['#proposta', 'textarea[name*="proposta"]', 'textarea#message']);
  if (proposalBox) {
    const subject = await visibleLocator(page, ['#assunto', '#subject', 'input[name*="assunto"]']);
    const price = await visibleLocator(page, ['#oferta', 'input[name*="oferta"]']);
    const finalPrice = await visibleLocator(page, ['#oferta-final', 'input[name*="oferta-final"]']);
    const duration = await visibleLocator(page, ['#duracao-estimada', 'input[name*="duracao"]']);
    if (subject) await subject.fill(draft.subject);
    if (price && draft.suggested_price != null) await price.fill(String(draft.suggested_price));
    if (duration) await duration.fill(String(draft.estimated_days));
    if (finalPrice && draft.suggested_price != null) await finalPrice.blur();
    await proposalBox.fill(draft.message);
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
    context = await chromium.launchPersistentContext(profileDir, {
      headless: false,
      ignoreDefaultArgs: ['--enable-automation'],
      args: ['--disable-blink-features=AutomationControlled'],
    });
    const page = context.pages()[0] || await context.newPage();
    await page.goto(listingUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await ask('Faça login manualmente no Chromium. Quando terminar, pressione Enter aqui: ');
    const links = targetJobUrl ? [{ href: targetJobUrl, text: targetJobUrl }] : await page.locator('a[href]').evaluateAll((anchors) => {
    const seen = new Set();
    return anchors.map((anchor) => ({ href: anchor.href, text: anchor.innerText })).filter(({ href, text }) => {
      if (!/[?&]fs=t(?:&|$)/.test(href) || !/\/project\/[^/?#]+-\d+/i.test(href) || !text.trim() || seen.has(href)) return false;
      seen.add(href); return true;
    });
    });
    let processed = 0;
    for (const item of links) {
    if (processed >= maxJobs) break;
    if (premium.test(item.text)) continue;
    const jobPage = await context.newPage();
    await jobPage.bringToFront();
    const result = await fillJob(jobPage, item.href);
    if (result.skipped) { console.log(`IGNORADA: ${result.skipped} — ${item.href}`); continue; }
    processed += 1;
    console.log(`${result.kind.toUpperCase()} preenchida: ${result.draft.subject || item.href}`);
    console.log(`Valor sugerido: R$ ${result.draft.suggested_price ?? 'a combinar'} | prazo: ${result.draft.estimated_days} dias`);
    console.log(`Texto preparado:\n${result.kind === 'question' ? result.draft.question : result.draft.message}`);
    const answer = await ask('Digite ENVIAR para clicar no envio desta vaga, ou Enter para deixar como rascunho: ');
    if (answer.trim() === 'ENVIAR') {
      const selectors = result.kind === 'question'
        ? ['#btnEnviarPergunta', 'button:has-text("Enviar mensagem")', 'button:has-text("Enviar pergunta")']
        : ['#enviar-proposta', 'button:has-text("Enviar proposta")'];
      const submit = await visibleLocator(jobPage, selectors);
      for (const selector of ['#confirmar-envio-proposta', '#confirmar-padrao-suspeito-mensagem']) {
        const checkbox = jobPage.locator(selector).first();
        if (await checkbox.count() && await checkbox.isVisible() && !await checkbox.isChecked()) await checkbox.check();
      }
      if (submit) {
        const responsePromise = jobPage.waitForResponse((response) =>
          response.request().method() === 'POST' && /\/services\/project\//.test(response.url()),
        { timeout: 15000 }).catch(() => null);
        await submit.click();
        const continueButton = await visibleLocator(jobPage, ['.modal:visible .btn-acao.continue']);
        if (continueButton) await continueButton.click();
        const response = await responsePromise;
        await jobPage.waitForLoadState('domcontentloaded').catch(() => {});
        if (response && !response.ok()) throw new Error(`Envio recusado pelo site (HTTP ${response.status()}).`);
        if (result.kind === 'question') {
          const confirmed = await verifyQuestion(jobPage, result.messagePageUrl, result.draft.question);
          if (!confirmed) throw new Error('O site não confirmou a mensagem na conversa; envio não será repetido automaticamente.');
          console.log(`ENVIO CONFIRMADO na conversa: ${jobPage.url()}`);
        } else if (response?.ok()) {
          console.log(`ENVIO CONFIRMADO pelo site (HTTP ${response.status()}). Página atual: ${jobPage.url()}`);
        } else {
          console.log('Clique realizado, mas sem confirmação inequívoca do site; o bot não repetirá automaticamente.');
        }
      }
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
