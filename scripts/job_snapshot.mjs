// Restrict analysis to the project description, excluding navigation and ads.
export async function readSnapshot(page) {
  const titleNode = page.locator('.box-project-view-container-title .nomeProjeto').first();
  if (!await titleNode.count()) throw new Error('Título da vaga não localizado; revisar seletores antes de orçar.');
  const title = await titleNode.textContent();
  const candidates = ['[itemprop="description"]', '#project-description',
    '.project-description', '.project-details .description'];
  let description = '';
  for (const selector of candidates) {
    const node = page.locator(selector).first();
    if (await node.count() && await node.isVisible()) {
      description = (await node.innerText()).trim();
      if (description) break;
    }
  }
  if (!description) throw new Error('Descrição isolada da vaga não localizada; revisar seletores antes de orçar.');
  const badge = page.locator('.box-project-view-principal > .flags img[alt*="Projeto exclusivo"], .box-project-view-principal > .flags img[src*="project_exclusive"], [data-project-premium="true"]');
  let isPremium = false;
  for (const node of await badge.all()) {
    if (await node.isVisible()) isPremium = true;
  }
  const budgetNode = page.locator('[data-budget-max]').first();
  const deadlineNode = page.locator('[data-deadline-days]').first();
  const budget = await budgetNode.count() ? Number(await budgetNode.getAttribute('data-budget-max')) : null;
  const deadline = await deadlineNode.count() ? Number(await deadlineNode.getAttribute('data-deadline-days')) : null;
  return { title: title.trim(), description, url: page.url(), is_premium: isPremium,
    budget_max: budget > 0 && Number.isFinite(budget) ? budget : null,
    deadline_days: deadline > 0 && Number.isFinite(deadline) ? deadline : null };
}
