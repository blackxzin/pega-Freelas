import { expect, test } from '@playwright/test';

const pageHtml = `<!doctype html>
<html lang="pt-BR"><body>
  <main><h1>Vaga mock: API FastAPI</h1>
    <form id="proposal-form">
      <label>Assunto <input id="subject" required></label>
      <label>Proposta <textarea id="message" required></textarea></label>
      <button type="submit">Enviar proposta</button>
    </form>
    <p id="result" role="status"></p>
  </main>
  <script>
    document.querySelector('#proposal-form').addEventListener('submit', event => {
      event.preventDefault();
      document.querySelector('#result').textContent = 'Proposta enviada ao ambiente mock';
    });
  </script>
</body></html>`;

test('preenche e envia proposta somente no ambiente mock', async ({ page }) => {
  await page.setContent(pageHtml);
  await expect(page.getByRole('heading', { name: 'Vaga mock: API FastAPI' })).toBeVisible();
  await page.locator('#subject').fill('Proposta: API FastAPI');
  await page.locator('#message').fill('Proposta validada para ambiente de teste.');
  await page.getByRole('button', { name: 'Enviar proposta' }).click();
  await expect(page.getByRole('status')).toHaveText('Proposta enviada ao ambiente mock');
});
