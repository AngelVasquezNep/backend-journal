/** Real public-flow acceptance covers persisted private chat, sources, refusals and reload recovery. */
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

test('saved chat requires first-party login', async ({ page }) => {
  await page.goto('/chat');
  await expect(page).toHaveURL(/\/login$/u);
});

test('admin uploads an original and receives a saved grounded answer with a current source', async ({ page }) => {
  test.setTimeout(150000);
  const privateConfig: { email?: string; replacement?: string } = process.env.TASKIFY_E2E_CREDENTIALS ? JSON.parse(readFileSync(process.env.TASKIFY_E2E_CREDENTIALS, 'utf8')) as { email?: string; replacement?: string } : {};
  test.skip(!privateConfig.email || !privateConfig.replacement, 'Requires private CLI-provisioned admin credentials and the complete stack.');
  await page.goto('/login');
  await page.getByLabel('Email').fill(privateConfig.email ?? '');
  await page.getByLabel('Password', { exact: true }).fill(privateConfig.replacement ?? '');
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL(/\/chat$/u);
  await page.getByRole('link', { name: 'Manage knowledge' }).click();
  const title = `Leave policy ${crypto.randomUUID()}`;
  await page.getByLabel('Title').fill(title);
  await page.getByLabel('Original file').setInputFiles({ name: 'leave-policy.txt', mimeType: 'text/plain', buffer: Buffer.from('Company leave policy grants 20 days of annual leave. The leave allowance applies to full time employees.') });
  await page.getByRole('button', { name: 'Upload knowledge' }).click();
  const resource = page.getByRole('listitem').filter({ has: page.getByRole('heading', { name: title, exact: true }) });
  await expect(resource.getByRole('status')).toHaveText('Ready', { timeout: 120000 });
  await page.getByRole('link', { name: 'Chat', exact: true }).click();
  await page.getByRole('textbox', { name: 'Question', exact: true }).fill('What is the company leave allowance?');
  await page.getByRole('textbox', { name: 'Question', exact: true }).press('Enter');
  await expect(page.getByRole('heading', { name: 'Company answer' }).last()).toBeVisible({ timeout: 30000 });
  await expect(page.getByRole('log')).toContainText('20 days');
  const source = page.getByRole('button', { name: `Download original file: ${title}`, exact: true }).last();
  await expect(source).toBeEnabled();
  const download = page.waitForEvent('download');
  await source.click();
  expect((await download).suggestedFilename()).toBe('leave-policy.txt');
  await page.reload();
  await expect(page.getByRole('log')).toContainText('20 days');
  await expect(page.getByRole('textbox', { name: 'Question', exact: true })).toBeEnabled();
  await page.getByRole('textbox', { name: 'Question', exact: true }).fill('What is the weather?');
  await page.getByRole('button', { name: 'Send question' }).click();
  await expect(page.getByRole('heading', { name: 'Insufficient company information' }).last()).toBeVisible({ timeout: 30000 });
  await page.getByRole('textbox', { name: 'Question', exact: true }).fill('Create Python code about the company leave policy.');
  await page.getByRole('button', { name: 'Send question' }).click();
  await expect(page.getByRole('heading', { name: 'Outside company-information scope' }).last()).toBeVisible({ timeout: 30000 });
  await page.getByRole('button', { name: 'Log out' }).click();
  await expect(page).toHaveURL(/\/login$/u);
});
