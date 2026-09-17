import { test, expect } from '@playwright/test';
import { readSnapshot } from '../scripts/job_snapshot.mjs';
import { spawnSync } from 'node:child_process';
import { hasExactMessage, hasPriorProjectIntroduction } from '../scripts/submission_guard.mjs';

test('isola descrição e gera pergunta em Python sem preço fechado', async ({ page }) => {
  await page.setContent('<nav>Assinar Premium</nav><h1 class="box-project-view-container-title"><span class="nomeProjeto">Automação Python</span></h1>' +
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
  expect(draft.question).toContain('podemos combinar um valor justo');
  expect(draft.question).toContain('equipe de dois desenvolvedores full stack que trabalham juntos');
});

test('descrição desconhecida bloqueia orçamento em vez de usar anúncios da página', async ({ page }) => {
  await page.setContent('<h1 class="box-project-view-container-title"><span class="nomeProjeto">Projeto</span></h1><nav>Premium API R$ 50</nav>');
  await expect(readSnapshot(page)).rejects.toThrow('Descrição isolada');
});

test('restrição explícita do projeto entra no snapshot', async ({ page }) => {
  await page.setContent('<h1 class="box-project-view-container-title"><span class="nomeProjeto">Projeto</span></h1><div id="project-description">API Python</div>' +
    '<span data-project-premium="true">Restrito</span>');
  expect((await readSnapshot(page)).is_premium).toBe(true);
});

test('trava de envio reconhece mensagem idêntica mesmo com espaços diferentes', () => {
  expect(hasExactMessage(['Olá!  Somos dois desenvolvedores\nfull stack.'],
    'Olá! Somos dois desenvolvedores full stack.')).toBe(true);
});

test('trava reconhece apresentação anterior da equipe para o mesmo projeto', () => {
  const messages = ['Somos dois desenvolvedores full stack que trabalham juntos e temos interesse no projeto “Site da Loja”.'];
  expect(hasPriorProjectIntroduction(messages, 'Site da Loja')).toBe(true);
  expect(hasPriorProjectIntroduction(messages, 'Outro Projeto')).toBe(false);
});
