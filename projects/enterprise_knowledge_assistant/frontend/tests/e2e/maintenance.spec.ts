/** Maintenance is an authenticated admin capability, never part of the user knowledge view. */
import { expect, test } from '@playwright/test';

test('knowledge maintenance requires login', async ({ page }) => {
  await page.goto('/admin/knowledge');
  await expect(page).toHaveURL(/\/login$/u);
});

test('admin can rename, replace and explicitly remove a resource without changing old source identity', async ({ page }) => {
  test.setTimeout(150000);
  const { readFileSync } = await import('node:fs');
  const config: { email?: string; replacement?: string } = process.env.TASKIFY_E2E_CREDENTIALS ? JSON.parse(readFileSync(process.env.TASKIFY_E2E_CREDENTIALS, 'utf8')) as { email?: string; replacement?: string } : {};
  test.skip(!config.email || !config.replacement, 'Requires private CLI-provisioned admin credentials and complete stack.');
  await page.goto('/login');
  await page.getByLabel('Email').fill(config.email ?? '');
  await page.getByLabel('Password', { exact: true }).fill(config.replacement ?? '');
  await page.getByRole('button', { name: 'Log in' }).click();
  await page.getByRole('link', { name: 'Manage knowledge' }).click();
  const title = `Maintenance ${crypto.randomUUID()}`;
  await page.getByLabel('Title', { exact: true }).fill(title);
  await page.getByLabel('Original file', { exact: true }).setInputFiles({ name: 'before.txt', mimeType: 'text/plain', buffer: Buffer.from('Company quartz benefit is 15 days.') });
  await page.getByRole('button', { name: 'Upload knowledge' }).click();
  let resource = page.getByRole('listitem').filter({ has: page.getByRole('heading', { name: title, exact: true }) });
  await expect(resource.getByRole('status')).toHaveText('Ready', { timeout: 120000 });
  const renamed = `${title} revised`;
  await resource.getByLabel(`Edit title: ${title}`, { exact: true }).fill(renamed);
  await resource.getByRole('button', { name: 'Save title' }).click();
  resource = page.getByRole('listitem').filter({ has: page.getByRole('heading', { name: renamed, exact: true }) });
  await expect(resource.getByRole('heading', { name: renamed, exact: true })).toBeVisible();
  await resource.getByLabel(`Replacement file: ${renamed}`, { exact: true }).setInputFiles({ name: 'after.txt', mimeType: 'text/plain', buffer: Buffer.from('Company quartz benefit is 18 days.') });
  await resource.getByRole('button', { name: 'Replace original' }).click();
  await expect(resource.getByText('Current original: after.txt', { exact: true })).toBeVisible({ timeout: 120000 });
  await resource.getByRole('button', { name: 'Remove item' }).click();
  await expect(resource.getByRole('button', { name: 'Confirm removal' })).toBeVisible();
  await resource.getByRole('button', { name: 'Cancel removal' }).click();
  await expect(resource.getByRole('heading', { name: renamed, exact: true })).toBeVisible();
  await resource.getByRole('button', { name: 'Remove item' }).click();
  await resource.getByRole('button', { name: 'Confirm removal' }).click();
  await expect(page.getByRole('heading', { name: renamed, exact: true })).toHaveCount(0);
});
