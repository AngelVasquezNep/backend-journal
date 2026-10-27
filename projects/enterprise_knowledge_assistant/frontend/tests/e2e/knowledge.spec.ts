/** US3 route-role acceptance uses operator-provisioned public-flow fixtures. */
import { expect, test } from '@playwright/test';

test('knowledge requires authentication and redirects to first-party login', async ({ page }) => {
  await page.goto('/knowledge');
  await expect(page).toHaveURL(/\/login$/u);
  await expect(page.getByLabel('Email')).toBeVisible();
});
