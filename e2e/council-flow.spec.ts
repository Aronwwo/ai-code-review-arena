import { test, expect, type Page, type Locator } from '@playwright/test';

const registerAndLogin = async (page: Page, suffix: string) => {
  await page.goto('/register');
  await page.fill('#email', `e2e-${suffix}@example.com`);
  await page.fill('#username', `e2e-${suffix}`);
  await page.fill('#password', 'Password123');
  await page.fill('#confirmPassword', 'Password123');
  await page.getByRole('button', { name: 'Utwórz Konto' }).click();
  await expect(page).toHaveURL(/\/projects/);
};

const createProject = async (page: Page, name: string) => {
  await page.getByRole('button', { name: 'Nowy Projekt' }).click();
  await page.fill('#name', name);
  await page.fill('#description', 'Projekt E2E');
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


test('council flow: login -> project -> upload -> review -> tabs', async ({ page }) => {
  const suffix = Date.now().toString();
  await registerAndLogin(page, suffix);

  await createProject(page, 'E2E Council Project');
  await addFile(page, 'main.py', "def total(items):\n    return sum(items)\n");

  await page.getByRole('button', { name: 'Konfiguruj Review' }).click();
  const dialog = page.getByRole('dialog');
  const startButton = dialog.getByRole('button', { name: /Rozpocznij/ });
  await expect(startButton).toBeDisabled();

  await dialog.getByText('Tryb Rady (Council)').click();
  await dialog.getByRole('tab', { name: /Agenci/ }).click();
  await configureVisibleSelectsToMock(dialog);

  await dialog.getByRole('tab', { name: /Moderator/ }).click();
  const moderatorSelects = dialog.locator('select:visible');
  await moderatorSelects.nth(1).selectOption('mock');
  await moderatorSelects.nth(2).selectOption('mock-model');

  await startButton.click();
  await expect(page).toHaveURL(/\/reviews\/\d+/);
  await expect(page.getByText('Podsumowanie Moderatora')).toBeVisible({ timeout: 60000 });

  await page.getByRole('tab', { name: /Dyskusje AI/ }).click();
  await expect(page.getByText('Dyskusje Agentów AI')).toBeVisible();

  await page.getByRole('tab', { name: /Pliki/ }).click();
  await expect(page.getByRole('heading', { name: 'main.py' })).toBeVisible();
});
