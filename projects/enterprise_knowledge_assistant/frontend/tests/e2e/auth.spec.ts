/** Public US2 browser acceptance uses credentials provisioned by the host operator CLI. */
import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

test('protected navigation requires first-party login and offers no external signup', async ({ page }) => {
  await page.goto('/chat');
  await expect(page).toHaveURL(/\/login$/u);
  await expect(page.getByLabel('Email')).toBeVisible();
  await expect(page.getByLabel('Password', { exact: true })).toBeVisible();
  await expect(page.getByText(/sign up|continue with google|continue with github/iu)).toHaveCount(0);
});

test('first login changes the initial password before protected access and logout', async ({ page }) => {
  const privateConfig: { email?: string; password?: string; replacement?: string } = process.env.TASKIFY_E2E_FIRST_LOGIN_CREDENTIALS ? JSON.parse(readFileSync(process.env.TASKIFY_E2E_FIRST_LOGIN_CREDENTIALS, 'utf8')) as { email?: string; password?: string; replacement?: string } : {};
  const email = process.env.TASKIFY_E2E_ADMIN_EMAIL ?? privateConfig.email;
  const password = process.env.TASKIFY_E2E_ADMIN_PASSWORD ?? privateConfig.password;
  const replacement = process.env.TASKIFY_E2E_NEW_PASSWORD ?? privateConfig.replacement;
  test.skip(!email || !password || !replacement, 'Requires private host-provisioned first-login credentials.');
  await page.goto('/login');
  await page.getByLabel('Email').fill(email ?? '');
  await page.getByLabel('Password', { exact: true }).fill(password ?? '');
  await page.getByRole('button', { name: 'Log in' }).click();
  await expect(page).toHaveURL(/\/change-password$/u);
  await page.getByLabel('Current password').fill(password ?? '');
  await page.getByLabel('New password', { exact: true }).fill(replacement ?? '');
  await page.getByLabel('Confirm new password').fill(replacement ?? '');
  await page.getByRole('button', { name: 'Change password' }).click();
  await expect(page).toHaveURL(/\/chat$/u);
  await page.getByRole('button', { name: 'Log out' }).click();
  await expect(page).toHaveURL(/\/login$/u);
});
