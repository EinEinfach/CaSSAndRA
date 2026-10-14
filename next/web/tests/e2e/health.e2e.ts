import { expect, test } from '@playwright/test';

test('API health endpoint answers', async ({ request }) => {
	const res = await request.get('/api/health');

	expect(res.ok()).toBe(true);
	expect(await res.json()).toMatchObject({ status: 'ok' });
});

test('start page shows server status', async ({ page }) => {
	await page.goto('/');

	await expect(page.getByRole('heading', { name: 'CaSSAndRA' })).toBeVisible();
	await expect(page.getByTestId('health')).toContainText('Server ok');
});

test('client routes are served by the SPA fallback', async ({ request }) => {
	const res = await request.get('/some/client/route');

	expect(res.status()).toBe(200);
	expect(res.headers()['content-type']).toContain('text/html');
});
