import { expect, test } from '@playwright/test';

// AT+V only asks the simulator for its version; it does not move the robot.
test('the log shows a typed command and its reply', async ({ page }) => {
	await page.goto('/');
	await page.getByRole('link', { name: 'Log' }).click();
	await expect(page.getByRole('heading', { name: 'Log', exact: true })).toBeVisible();

	await page.getByLabel('AT command').fill('AT+V');
	await page.getByRole('button', { name: 'Send' }).click();
	const sent = page.getByRole('list', { name: 'Sent commands' });
	await expect(sent.getByRole('listitem').first()).toContainText(/AT\+V\s*V,/);

	// The app logs the command; the view picks it up within a poll.
	const lines = page.getByRole('log', { name: 'Log lines' });
	await expect(lines).toContainText('cmd=raw line=AT+V', { timeout: 5_000 });
	await page.getByLabel('Filter log').fill('raw command reply');
	await expect(lines.locator('.line')).not.toHaveCount(0);

	await expect(page.getByText('CPU load')).toBeVisible();
	await expect(page.getByRole('alert')).toHaveCount(0);
});
