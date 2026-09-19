import { chromium } from '@playwright/test';
import { createInterface } from 'node:readline/promises';
import { stdin as input, stdout as output } from 'node:process';
import { spawnSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { readSnapshot } from './job_snapshot.mjs';
import { hasExactMessage, hasPriorProjectIntroduction } from './submission_guard.mjs';
import { firstLocator, selectors } from './selectors.mjs';
import { loadLocalEnv } from './local_env.mjs';
import { sendDiscordNotification } from './discord_notify.mjs';

const rl = createInterface({ input, output });
const ask = (question) => rl.question(question);
const root = fileURLToPath(new URL('..', import.meta.url));
loadLocalEnv(`${root}/.env`);
const profileDir = process.env.BROWSER_PROFILE_DIR || `${root}/browser-profile`;
mkdirSync(profileDir, { recursive: true });
const maxJobs = Number(process.env.MAX_JOBS || 5);
const listingUrl = process.env.JOBS_URL || 'https://www.99freelas.com.br/projects?categoria=web-mobile-e-software&page=4';
const targetJobUrl = process.env.TARGET_JOB_URL;
const automationMode = process.env.AUTOMATION_MODE || 'SEMI_AUTO';
const autoSend = process.env.AUTO_SEND === 'true' && automationMode === 'AUTO';
const dryRun = process.env.DRY_RUN !== 'false';
const killSwitch = process.env.AUTO_SEND_KILL_SWITCH !== 'false';
const minDelay = Math.max(0, Number(process.env.ACTION_DELAY_MIN_MS || 350));
const maxDelay = Math.max(minDelay, Number(process.env.ACTION_DELAY_MAX_MS || 1200));
const runForever = process.env.RUN_FOREVER === 'true';
const pollSeconds = Math.max(60, Number(process.env.HUNT_POLL_SECONDS || (Number(process.env.HUNT_INTERVAL_MINUTES || 15) * 60)));
const forceProposal = process.env.AUTO_FORCE_PROPOSAL === 'true';
const maxProposalsPerClient = Math.max(1, Number(process.env.MAX_PROPOSALS_PER_CLIENT_24H || 1));
const maxIdleCycles = Math.max(0, Number(process.env.STOP_AFTER_IDLE_CYCLES || 0));
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

function tracking(command, payload = {}) {
  const result = spawnSync('python', ['scripts/proposal_tracking.py', command], {
    cwd: root, input: JSON.stringify(payload), encoding: 'utf8',
  });
  if (result.status !== 0) throw new Error(result.stderr || `falha no tracking (${command})`);
  return result.stdout ? JSON.parse(result.stdout.trim().split('\n').pop()) : {};
}

function markSent(proposalId, externalId, conversationId) {
  const args = ['scripts/proposal_tracking.py', 'sent', '--proposal-id', String(proposalId), '--external-id', externalId || 'browser-confirmed'];
  if (conversationId) args.push('--conversation-id', conversationId);
  const result = spawnSync('python', args, { cwd: root, encoding: 'utf8' });
  if (result.status !== 0) throw new Error(result.stderr || 'falha ao registrar envio');
}

function conversationIdFromUrl(value) {
  const match = String(value || '').match(/\/messages\/(?:inbox\/)?([^/?#]+)/i);
  return match ? match[1] : undefined;
}

function brl(value) {
  return `R$ ${Number(value).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function forceProposalDraft(draft) {
  if (!forceProposal || draft.action !== 'question' || !Array.isArray(draft.price_range) || !draft.price_range[1]) return draft;
  const scope = (draft.breakdown || []).slice(0, 5).map((item) => item.deliverable).join('; ') || 'desenvolvimento, testes e entrega documentada';
  const days = Array.isArray(draft.days_range) && draft.days_range[1] ? draft.days_range[1] : null;
  if (!days) return draft;
  const title = String(draft.subject || '').replace(/^Proposta:\s*/i, '');
  draft.action = 'proposal';
  draft.questions = [];
  draft.suggested_price = draft.price_range[1];
  draft.estimated_days = days;
  draft.message = `Olá! Temos interesse no projeto “${title}”. Entendemos que a entrega envolve ${scope}. `
    + 'Somos uma equipe de dois desenvolvedores full stack que trabalham juntos. '
    + 'Propomos executar em etapas verificáveis, com alinhamento, implementação, testes e entrega documentada. '
    + `Como referência inicial, propomos ${brl(draft.suggested_price)} e prazo de até ${days} dias corridos. `
    + 'O preço pode ser negociado conforme os detalhes finais do escopo e as prioridades do projeto. '
    + 'APIs, hospedagem, domínio e serviços pagos ficam nas contas do cliente.';
  draft.validation_status = 'PENDING';
  draft.validation_reasons = ['Estimativa automática preliminar; confirmar escopo com o cliente.'];
  return draft;
}

function clientHistory(clientKey) {
  if (!clientKey) return {};
  const result = spawnSync('python', ['scripts/proposal_tracking.py', 'history', '--client-key', clientKey], { cwd: root, encoding: 'utf8' });
  if (result.status !== 0) return {};
  return JSON.parse(result.stdout.trim().split('\n').pop());
}

function clientContext(clientKey) {
  if (!clientKey) return [];
  const result = spawnSync('python', ['scripts/proposal_tracking.py', 'context', '--client-key', clientKey], { cwd: root, encoding: 'utf8' });
  if (result.status !== 0) return [];
  return JSON.parse(result.stdout.trim().split('\n').pop()).messages || [];
}

function claimSend(proposalId) {
  const result = spawnSync('python', ['scripts/proposal_tracking.py', 'claim', '--proposal-id', String(proposalId)], {
    cwd: root, encoding: 'utf8',
  });
  if (result.status !== 0) return false;
  return JSON.parse(result.stdout.trim().split('\n').pop()).claimed === true;
}

async function notifyPause(reason) {
  if (!process.env.DISCORD_WEBHOOK_URL) return;
  await sendDiscordNotification(process.env.DISCORD_WEBHOOK_URL, `⏸️ FreelaHunter pausado: ${reason}`);
}

async function visibleLocator(page, selectors) {
  return firstLocator(page, selectors, { visible: true });
}

async function humanPause() {
  const delay = minDelay + Math.random() * (maxDelay - minDelay);
  await new Promise((resolve) => setTimeout(resolve, Math.round(delay)));
}

async function conversationMessages(page, messagePageUrl) {
  await page.goto(messagePageUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
  const conversationLink = await firstLocator(page, selectors.conversation.link);
  if (conversationLink) {
    const href = await conversationLink.getAttribute('href');
    await page.goto(new URL(href, page.url()).href, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await humanPause();
  }
  for (const selector of selectors.conversation.message) {
    const messages = page.locator(selector);
    if (await messages.count()) return messages.allTextContents();
  }
  if (/\/messages\//i.test(page.url())) return [await page.locator('body').innerText()];
  return null;
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
  const wanted = String(expected || '').replace(/\s+/g, ' ').trim();
  if (messages?.some((message) => String(message).replace(/\s+/g, ' ').trim().includes(wanted))) return true;
  await page.goto('https://www.99freelas.com.br/messages/inbox', { waitUntil: 'domcontentloaded', timeout: 30000 });
  const inboxText = (await page.locator('body').innerText()).replace(/\s+/g, ' ').trim();
  return wanted.length > 40 && inboxText.includes(wanted.slice(0, 80));
}

async function fillJob(page, link) {
  await page.goto(link, { waitUntil: 'domcontentloaded', timeout: 30000 });
  let snapshot;
  try { snapshot = await readSnapshot(page); }
  catch (error) { return { skipped: error.message }; }
  snapshot.client_key = snapshot.client_url || snapshot.client;
  snapshot.client_history = clientHistory(snapshot.client_key);
  snapshot.confirmed_context = clientContext(snapshot.client_key);
  const draft = forceProposalDraft(generate(snapshot));
  if (draft.action === 'skip') return { skipped: draft.reason };
  console.log(JSON.stringify({ tasks: draft.breakdown, price_range: draft.price_range,
    client_total_range: draft.client_total_range, days_range: draft.days_range,
    questions: draft.questions, commercial_reference: draft.knowledge }, null, 2));
  if (draft.action === 'question') {
    const questionLink = await firstLocator(page, selectors.proposal.question_link);
    if (questionLink) {
      const href = await questionLink.getAttribute('href');
      await page.goto(new URL(href, page.url()).href, { waitUntil: 'domcontentloaded' });
    }
    const messagePageUrl = page.url();
    if (await alreadyContacted(page, messagePageUrl, draft)) {
      return { skipped: 'Conversa inicial desta vaga já existe; novo envio bloqueado para evitar duplicata.' };
    }
    const question = await visibleLocator(page, selectors.proposal.question);
    if (!question) {
      console.log(draft.question);
      return { skipped: 'Escopo exige esclarecimento; formulário de pergunta não localizado.' };
    }
    await question.fill(draft.question);
    await humanPause();
    return { kind: 'question', draft, messagePageUrl, snapshot };
  }
  const bidLink = await firstLocator(page, selectors.proposal.bid_link);
  if (!bidLink) {
    return { skipped: 'Candidatura indisponível ou proposta já existente; envio bloqueado para evitar duplicata.' };
  }
  const href = await bidLink.getAttribute('href');
  await page.goto(new URL(href, page.url()).href, { waitUntil: 'domcontentloaded' });
  const proposalBox = await visibleLocator(page, selectors.proposal.message);
  if (proposalBox) {
    const subject = await visibleLocator(page, selectors.proposal.subject);
    const price = await visibleLocator(page, selectors.proposal.price);
    const finalPrice = await visibleLocator(page, selectors.proposal.final_price);
    const duration = await visibleLocator(page, selectors.proposal.duration);
    if (subject) { await subject.fill(draft.subject); await humanPause(); }
    if (price && draft.suggested_price != null) { await price.fill(String(draft.suggested_price)); await humanPause(); }
    if (duration) { await duration.fill(String(draft.estimated_days)); await humanPause(); }
    if (finalPrice && draft.suggested_price != null) await finalPrice.blur();
    await proposalBox.fill(draft.message);
    await humanPause();
    return { kind: 'proposal', draft, snapshot };
  }
  const question = await visibleLocator(page, selectors.proposal.question);
  if (question) {
    await question.fill(draft.question);
    await humanPause();
    return { kind: 'question', draft, messagePageUrl: page.url(), snapshot };
  }
  return { skipped: 'form not found' };
}

async function main() {
  if (autoSend && (dryRun || killSwitch)) {
    throw new Error('AUTO mode exige DRY_RUN=false e AUTO_SEND_KILL_SWITCH=false.');
  }
  console.log(JSON.stringify({ event: 'hunt_started', auto_send: autoSend, dry_run: dryRun,
    run_forever: runForever, force_proposal: forceProposal, poll_seconds: pollSeconds,
    max_jobs: maxJobs, max_proposals_per_client_24h: maxProposalsPerClient,
    stop_after_idle_cycles: maxIdleCycles }));
  let context;
  try {
    context = await chromium.launchPersistentContext(profileDir, {
      headless: false,
      ignoreDefaultArgs: ['--enable-automation'],
      args: ['--disable-blink-features=AutomationControlled'],
    });
    const page = context.pages()[0] || await context.newPage();
    let firstCycle = true;
    let idleCycles = 0;
    while (true) {
    await page.goto(listingUrl, { waitUntil: 'domcontentloaded', timeout: 30000 });
    if (firstCycle && process.env.AUTO_LOGIN_PROMPT !== 'false' && !autoSend) await ask('Faça login manualmente no Chromium. Quando terminar, pressione Enter aqui: ');
    const links = targetJobUrl ? [{ href: targetJobUrl, text: targetJobUrl }] : await (async () => {
      const collected = [];
      for (const selector of selectors.listing.links) {
        const rows = await page.locator(selector).evaluateAll((anchors) => anchors.map((anchor) => ({ href: anchor.href, text: anchor.innerText })));
        collected.push(...rows);
      }
      const seen = new Set();
      return collected.filter(({ href, text }) => {
        if (!/\/project\/[^/?#]+-\d+/i.test(href) || !text.trim() || seen.has(href)) return false;
        seen.add(href); return true;
      });
    })();
    let processed = 0;
    let cycleSent = 0;
    for (const item of links) {
    if (processed >= maxJobs) break;
    if (premium.test(item.text)) continue;
    const jobPage = await context.newPage();
    await jobPage.bringToFront();
    await humanPause();
    const result = await fillJob(jobPage, item.href);
    try {
    if (result.skipped) { console.log(`IGNORADA: ${result.skipped} — ${item.href}`); continue; }
    if (result.draft.validation_status && result.draft.validation_status !== 'PASSED' && !forceProposal) {
      console.log(`IGNORADA: proposta não passou validação — ${(result.draft.validation_reasons || []).join('; ')}`);
      continue;
    }
    console.log(`${result.kind.toUpperCase()} preenchida: ${result.draft.subject || item.href}`);
    console.log(`Valor sugerido: R$ ${result.draft.suggested_price ?? 'a combinar'} | prazo: ${result.draft.estimated_days} dias`);
    console.log(`Texto preparado:\n${result.kind === 'question' ? result.draft.question : result.draft.message}`);
    const clientGate = tracking('client-gate', {
      client_key: result.snapshot.client_key,
      max_per_day: maxProposalsPerClient,
    });
    const messageOnClientLimit = process.env.AUTO_MESSAGE_ON_LIMIT === 'true'
      && result.kind === 'question' && !clientGate.allowed;
    if (!clientGate.allowed) {
      if (!messageOnClientLimit) {
        console.log(`IGNORADA: ${clientGate.reason} — ${item.href}`);
        continue;
      }
      console.log(`LIMITE DE PROPOSTAS: tentando enviar mensagem ao cliente — ${item.href}`);
    }
    const tracked = tracking('register', {
      url: result.snapshot.url, title: result.snapshot.title, subject: result.draft.subject,
      message: result.kind === 'question' ? result.draft.question : result.draft.message,
      price: result.draft.suggested_price, project_type: result.snapshot.category || result.snapshot.title,
      client_key: result.snapshot.client_url || result.snapshot.client,
      validation_status: result.draft.validation_status || 'PENDING',
    });
    if (tracked.already_sent) {
      console.log(`IGNORADA: proposta já enviada anteriormente — ${item.href}`);
      continue;
    }
    processed += 1;
    const answer = autoSend ? 'ENVIAR' : await ask('Digite ENVIAR para clicar no envio desta vaga, ou Enter para deixar como rascunho: ');
    if (answer.trim() === 'ENVIAR') {
    if (!messageOnClientLimit) {
      const gate = spawnSync('python', ['scripts/proposal_tracking.py', 'gate', '--max-per-hour', process.env.MAX_PROPOSALS_PER_HOUR || '3', '--max-per-day', process.env.MAX_PROPOSALS_PER_DAY || '10', '--no-response-days', process.env.PAUSE_NO_RESPONSE_DAYS || '7', '--consecutive-no-response', process.env.PAUSE_CONSECUTIVE_NO_RESPONSE || '5', '--rejection-threshold', process.env.PAUSE_REJECTION_THRESHOLD || '0.6'], { cwd: root, encoding: 'utf8' });
      if (gate.status !== 0) {
        const reason = gate.stdout?.trim().split('\n').pop() || gate.stderr;
        console.log(`PAUSADA: ${reason}`);
        try { await notifyPause(reason); } catch (error) { console.log(`Falha ao avisar pausa: ${error.message}`); }
        continue;
      }
    }
      const submit = await visibleLocator(jobPage, result.kind === 'question' ? selectors.proposal.submit_question : selectors.proposal.submit_proposal);
      for (const selector of selectors.proposal.confirmations) {
        const checkbox = jobPage.locator(selector).first();
        if (await checkbox.count() && await checkbox.isVisible() && !await checkbox.isChecked()) await checkbox.check();
      }
      if (submit) {
        if (!claimSend(tracked.proposal_id)) {
          console.log('IGNORADA: outro processo já reservou ou enviou esta proposta.');
          continue;
        }
        const responsePromise = jobPage.waitForResponse((response) =>
          response.request().method() === 'POST' && /\/services\/project\//.test(response.url()),
        { timeout: 15000 }).catch(() => null);
        await submit.click();
        const continueButton = await visibleLocator(jobPage, selectors.proposal.continue_modal);
        if (continueButton) await continueButton.click();
        const response = await responsePromise;
        await jobPage.waitForLoadState('domcontentloaded').catch(() => {});
        if (response && !response.ok()) throw new Error(`Envio recusado pelo site (HTTP ${response.status()}).`);
        if (result.kind === 'question') {
          const confirmed = await verifyQuestion(jobPage, result.messagePageUrl, result.draft.question);
          if (!confirmed) throw new Error('O site não confirmou a mensagem na conversa; envio não será repetido automaticamente.');
          markSent(tracked.proposal_id, `question-${tracked.proposal_id}`, conversationIdFromUrl(jobPage.url()));
          cycleSent += 1;
          console.log(`${messageOnClientLimit ? 'MENSAGEM' : 'ENVIO'} CONFIRMADO na conversa: ${jobPage.url()}`);
        } else if (response?.ok()) {
          markSent(tracked.proposal_id, `proposal-${tracked.proposal_id}`, conversationIdFromUrl(jobPage.url()));
          cycleSent += 1;
          console.log(`ENVIO CONFIRMADO pelo site (HTTP ${response.status()}). Página atual: ${jobPage.url()}`);
        } else {
          console.log('Clique realizado, mas sem confirmação inequívoca do site; o bot não repetirá automaticamente.');
        }
      }
      else console.log('Botão de envio não localizado; rascunho preservado.');
    }
    } catch (error) {
      console.error(`FALHA na vaga ${item.href}: ${error.message}`);
    } finally {
      await jobPage.close().catch(() => {});
    }
    }
    idleCycles = cycleSent === 0 ? idleCycles + 1 : 0;
    console.log(`Ciclo concluído: ${processed} vaga(s), ${cycleSent} envio(s). Chromium permanece aberto.`);
    if (runForever && maxIdleCycles > 0 && idleCycles >= maxIdleCycles) {
      console.log(`Caça encerrada após ${idleCycles} ciclo(s) sem envio para economizar créditos.`);
      break;
    }
    if (!runForever) {
      await ask('Pressione Enter para fechar Chromium: ');
      break;
    }
    firstCycle = false;
    await page.waitForTimeout(pollSeconds * 1000);
    }
  } finally {
    if (context) await context.close();
    rl.close();
  }
}

main().catch((error) => { console.error(error.message); rl.close(); process.exitCode = 1; });
