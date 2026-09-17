import { test, expect } from '@playwright/test';
import { readSnapshot } from '../scripts/job_snapshot.mjs';
import { spawnSync } from 'node:child_process';

test('isola descrição e gera pergunta em Python sem preço fechado', async ({ page }) => {
  await page.setContent('<nav>Assinar Premium</nav><h1>Automação Python</h1>' +
    '<div id="project-description">Automatizar relatórios da empresa.</div>');
  const snapshot = await readSnapshot(page);
  expect(snapshot.description).not.toContain('Premium');
  const result = spawnSync('python', ['scripts/generate_proposal.py'], {
    input: JSON.stringify(snapshot), encoding: 'utf8',
  });
  expect(result.status).toBe(0);
  const draft = JSON.parse(result.stdout);
  expect(draft.action).toBe('question');
  expect(draft.suggested_price).toBeNull();
  expect(draft.question).toContain('combinar o preço');
});

test('descrição desconhecida bloqueia orçamento em vez de usar anúncios da página', async ({ page }) => {
  await page.setContent('<h1>Projeto</h1><nav>Premium API R$ 50</nav>');
  await expect(readSnapshot(page)).rejects.toThrow('Descrição isolada');
});

test('restrição explícita do projeto entra no snapshot', async ({ page }) => {
  await page.setContent('<h1>Projeto</h1><div id="project-description">API Python</div>' +
    '<span data-premium="true">Restrito</span>');
  expect((await readSnapshot(page)).is_premium).toBe(true);
});
