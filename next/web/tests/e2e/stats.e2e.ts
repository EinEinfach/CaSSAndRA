import { expect, test } from '@playwright/test';

// The binary records one sample per minute, so the charts may still be empty.
test('the statistics page loads a time span', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('link', { name: 'Stats' }).click();
	await expect(page.getByRole('heading', { name: 'Statistics' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'Time' })).toBeVisible();
	await expect(page.getByRole('heading', { name: 'History' })).toBeVisible();
	const answer = page.waitForResponse((r) => r.url().includes('/api/stats?') && r.ok());
	await page.getByText('7 days', { exact: true }).click();
	await answer;
	await expect(page.getByRole('alert')).toHaveCount(0);
});
