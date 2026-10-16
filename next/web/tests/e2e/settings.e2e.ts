import { expect, test } from '@playwright/test';

test('change a setting, save it and find it after a reload', async ({ page }) => {
	await page.goto('/settings');
	const speed = page.getByLabel(/Mow speed/);
	await expect(speed).toHaveValue(/\d/);
	const before = await speed.inputValue();
	const next = before === '0.33' ? '0.34' : '0.33';

	await speed.fill(next);
	await expect(page.getByText('Unsaved changes')).toBeVisible();
	await page.getByRole('button', { name: 'Save' }).click();
	await expect(page.getByRole('status')).toHaveText('Saved');

	await page.reload();
	await expect(page.getByLabel(/Mow speed/)).toHaveValue(next);
});

test('invalid values are explained and not saved', async ({ page }) => {
	await page.goto('/settings');
	await page.getByLabel(/Lane width/).fill('5');
	await page.getByRole('button', { name: 'Save' }).click();
	await expect(page.getByRole('alert')).toContainText('planner.widthM');
	await page.getByRole('button', { name: 'Discard' }).click();
	await expect(page.getByRole('alert')).toHaveCount(0);
});

test('robot pictures are served and the choice is kept', async ({ page }) => {
	const picture = page.waitForResponse((r) => r.url().endsWith('/rovers/landrumower.png'));
	await page.goto('/settings');
	const res = await picture;
	expect(res.status()).toBe(200);
	expect(res.headers()['content-type']).toBe('image/png');

	await page.getByText('Landrumower', { exact: true }).click();
	await page.getByRole('button', { name: 'Save' }).click();
	await expect(page.getByRole('status')).toHaveText('Saved');
	await page.reload();
	await expect(page.getByRole('radio', { name: 'Landrumower' })).toBeChecked();

	// Restore the default for the other tests.
	await page.getByText('Default', { exact: true }).click();
	await page.getByRole('button', { name: 'Save' }).click();
	await expect(page.getByRole('status')).toHaveText('Saved');
});
