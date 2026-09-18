import { firstLocator, selectors } from './selectors.mjs';

// Restrict analysis to the project description, excluding navigation and ads.
export async function readSnapshot(page) {
  const titleNode = await firstLocator(page, selectors.job.title);
  if (!titleNode) throw new Error('Título da vaga não localizado; revisar seletores antes de orçar.');
  const title = await titleNode.textContent();
  const candidates = selectors.job.description;
  let description = '';
  for (const selector of candidates) {
    const node = page.locator(selector).first();
    if (await node.count() && await node.isVisible()) {
      description = (await node.innerText()).trim();
      if (description) break;
    }
  }
  if (!description) throw new Error('Descrição isolada da vaga não localizada; revisar seletores antes de orçar.');
  let isPremium = false;
  for (const selector of selectors.job.premium_badge) {
    const badge = page.locator(selector);
    for (const node of await badge.all()) {
      if (await node.isVisible()) isPremium = true;
    }
  }
  const budgetNode = await firstLocator(page, selectors.job.budget);
  const deadlineNode = await firstLocator(page, selectors.job.deadline);
  const clientNode = await firstLocator(page, selectors.job.client);
  const clientLink = await firstLocator(page, selectors.job.client_link);
  const budgetText = budgetNode ? await budgetNode.innerText().catch(() => '') : '';
  const deadlineText = deadlineNode ? await deadlineNode.innerText().catch(() => '') : '';
  const budgetRaw = budgetNode ? await budgetNode.getAttribute('data-budget-max') || await budgetNode.getAttribute('content') : null;
  const deadlineRaw = deadlineNode ? await deadlineNode.getAttribute('data-deadline-days') || await deadlineNode.getAttribute('content') : null;
  const budget = Number(budgetRaw) || Number((budgetText.match(/R\$\s*([\d.,]+)/i) || [])[1]?.replace('.', '').replace(',', '.') || 0);
  const deadline = Number(deadlineRaw) || Number((deadlineText.match(/(\d+)\s*dias?/i) || [])[1] || 0);
  const client = clientNode ? (await clientNode.textContent()).trim() : '';
  const clientUrl = clientLink ? await clientLink.getAttribute('href') : '';
  return { title: title.trim(), description, client, url: page.url(), is_premium: isPremium,
    client_url: clientUrl ? new URL(clientUrl, page.url()).href : '',
    budget_max: budget > 0 && Number.isFinite(budget) ? budget : null,
    deadline_days: deadline > 0 && Number.isFinite(deadline) ? deadline : null };
}
