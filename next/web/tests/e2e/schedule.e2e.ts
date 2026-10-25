import { expect, test } from '@playwright/test';

// The schedule stays switched off here: it would start the shared simulated
// robot in the middle of other tests.

const off = { start: '12:00', end: '12:00', taskIds: [] };

test.afterAll(async ({ request }) => {
	await request.put('/api/schedule', {
		data: { schedule: { active: false, days: Array.from({ length: 7 }, () => off) } }
	});
});

test('plan a window and keep it after reloading', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('link', { name: 'Schedule' }).click();
	await expect(page.getByRole('heading', { name: 'Schedule' })).toBeVisible();
	await expect(page.getByTestId('schedule-status')).toHaveText('The schedule is off.');

	await page.getByLabel('Mow on Wednesday').check();
	await page.getByLabel('Wednesday from').selectOption('07:30');
	await page.getByLabel('Wednesday until').selectOption('11:00');
	await expect(page.getByText('Unsaved changes')).toBeVisible();
	await page.getByRole('button', { name: 'Save' }).click();
	await expect(page.getByRole('status').filter({ hasText: 'Saved' })).toBeVisible();

	await page.reload();
	await expect(page.getByLabel('Wednesday from')).toHaveValue('07:30');
	await expect(page.getByLabel('Wednesday until')).toHaveValue('11:00');
	await expect(page.getByLabel('Mow on Monday')).not.toBeChecked();
});
