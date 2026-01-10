import { test, expect, type Page, type Locator } from '@playwright/test';

const registerAndLogin = async (page: Page, suffix: string) => {
  await page.goto('/register');
  await page.fill('#email', `arena-${suffix}@example.com`);
  await page.fill('#username', `arena-${suffix}`);
  await page.fill('#password', 'Password123');
  await page.fill('#confirmPassword', 'Password123');
  await page.getByRole('button', { name: 'Utwórz Konto' }).click();
  await expect(page).toHaveURL(/\/projects/);
};

const createProject = async (page: Page, name: string) => {
  await page.getByRole('button', { name: 'Nowy Projekt' }).click();
  await page.fill('#name', name);
  await page.fill('#description', 'Projekt Arena');
  await page.getByRole('button', { name: 'Utwórz Projekt' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
  await page.getByRole('link', { name }).click();
};

const addFile = async (page: Page, name: string, content: string) => {
  await page.getByRole('button', { name: 'Dodaj Plik' }).click();
  await page.fill('#filename', name);
  await page.fill('#language', 'python');
  await page.fill('#content', content);
  await page.getByRole('button', { name: 'Dodaj Plik' }).click();
  await expect(page.getByRole('dialog')).toBeHidden();
};

const configureVisibleSelectsToMock = async (dialog: Locator) => {
  const selects = dialog.locator('select:visible');
  const count = await selects.count();
  for (let i = 0; i < count; i += 2) {
    await selects.nth(i).selectOption('mock');
    await selects.nth(i + 1).selectOption('mock-model');
  }
};

const fillVisibleTextareas = async (dialog: Locator, prefix: string) => {
  const textareas = dialog.locator('textarea:visible');
  const count = await textareas.count();
  for (let i = 0; i < count; i += 1) {
    await textareas.nth(i).fill(`${prefix} ${i + 1}`);
  }
};

test('arena flow: setup schemas -> vote -> rankings', async ({ page }) => {
  const suffix = Date.now().toString();
  await registerAndLogin(page, suffix);

  await createProject(page, 'E2E Arena Project');
  await addFile(page, 'arena.py', "def compute(x):\n    return x * 2\n");

  await page.getByRole('button', { name: 'Konfiguruj Review' }).click();
  const dialog = page.getByRole('dialog');
  await dialog.getByText('Tryb Areny (Arena)').click();

  await dialog.getByRole('tab', { name: /Schema A/ }).click();
  await configureVisibleSelectsToMock(dialog);
  await fillVisibleTextareas(dialog, 'Schema A prompt');

  await dialog.getByRole('tab', { name: /Schema B/ }).click();
  await configureVisibleSelectsToMock(dialog);
  await fillVisibleTextareas(dialog, 'Schema B prompt');

  await dialog.getByRole('button', { name: /Rozpocznij Arena/ }).click();
  await expect(page).toHaveURL(/\/arena\/sessions\/\d+/);

  const voteButton = page.getByRole('button', { name: 'Zapisz Głos' });
  await expect(voteButton).toBeVisible({ timeout: 120000 });

  await page.getByRole('button', { name: 'Schema A' }).click();
  await voteButton.click();

  await expect(page.getByText('Zwycięzca: Schema A')).toBeVisible({ timeout: 60000 });
  await page.getByRole('button', { name: 'Zobacz Rankingi' }).click();

  await expect(page.getByRole('heading', { name: 'Arena Rankings' })).toBeVisible();
  const votesCard = page.getByText('Całkowite Głosy').locator('..').locator('..');
  const votesText = await votesCard.textContent();
  const votesMatch = votesText?.match(/\d+/);
  const votesCount = votesMatch ? Number(votesMatch[0]) : 0;
  expect(votesCount).toBeGreaterThan(0);
});
