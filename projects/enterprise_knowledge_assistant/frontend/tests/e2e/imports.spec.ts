/** Smoke browser harness verifies source alias imports and the built entry-point shell. */
import { expect, test } from '@playwright/test';
import { APPLICATION_NAME } from '@/composition/title';

test('boots the accessible shell with source imports resolved', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(APPLICATION_NAME);
  await expect(page.getByRole('main').getByRole('heading', { name: APPLICATION_NAME })).toBeVisible();
});
