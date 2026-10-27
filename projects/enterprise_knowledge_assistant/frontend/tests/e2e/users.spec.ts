/** User provisioning browser acceptance requires a prepared host admin and first-party sessions. */
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

test('user provisioning requires authentication', async ({ page }) => {
  await page.goto('/admin/users');
  await expect(page).toHaveURL(/\/login$/u);
});

test('admin creates a user who must change the password before read-only access', async ({ page }) => {
  const privateConfig: { email?: string; replacement?: string } = process.env.TASKIFY_E2E_CREDENTIALS ? JSON.parse(readFileSync(process.env.TASKIFY_E2E_CREDENTIALS, 'utf8')) as { email?: string; replacement?: string } : {};
  const email = process.env.TASKIFY_E2E_ADMIN_EMAIL ?? privateConfig.email;
  const password = process.env.TASKIFY_E2E_ADMIN_PASSWORD ?? privateConfig.replacement;
  test.skip(!email || !password, 'Requires private host-provisioned admin credentials.');
  const userEmail = `client-${crypto.randomUUID()}@example.test`;
  const initial = `Initial-${crypto.randomUUID()}`;
  const changed = `Changed-${crypto.randomUUID()}`;
  await page.goto('/login');
  await page.getByLabel('Email').fill(email ?? '');
  await page.getByLabel('Password', { exact: true }).fill(password ?? '');
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL(/\/chat$/u);
  await page.getByRole('link', { name: 'Create user' }).click();
  await expect(page.getByLabel(/company|role/iu)).toHaveCount(0);
  await page.getByLabel('Display name').fill('Browser Client');
  await page.getByLabel('Email').fill(userEmail);
  await page.getByLabel('Initial password').fill(initial);
  await page.getByRole('button', { name: 'Create user' }).click();
  await expect(page.getByRole('status')).toContainText('User created');
  await expect(page.getByLabel('Initial password')).toHaveValue('');
  await page.getByRole('button', { name: 'Log out' }).click();
  await expect(page).toHaveURL(/\/login$/u);
  await page.getByLabel('Email').fill(userEmail);
  await page.getByLabel('Password', { exact: true }).fill(initial);
  await expect(page.getByLabel('Email')).toHaveValue(userEmail);
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL(/\/change-password$/u);
  await page.getByLabel('Current password').fill(initial);
  await page.getByLabel('New password', { exact: true }).fill(changed);
  await page.getByLabel('Confirm new password').fill(changed);
  await page.getByRole('button', { name: 'Change password' }).click();
  await expect(page).toHaveURL(/\/chat$/u);
  await expect(page.getByRole('link', { name: 'Create user' })).toHaveCount(0);
  await page.goto('/admin/users');
  await expect(page.getByRole('heading', { name: 'Create company user' })).toHaveCount(0);
});
