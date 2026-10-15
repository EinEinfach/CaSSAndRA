import { expect, test } from '@playwright/test';

test('API health endpoint answers', async ({ request }) => {
	const res = await request.get('/api/health');

	expect(res.ok()).toBe(true);
	expect(await res.json()).toMatchObject({ status: 'ok' });
});

test('start page shows the app and its version', async ({ page, request }) => {
	const { version } = await (await request.get('/api/health')).json();
	await page.goto('/');

	const nav = page.getByRole('navigation', { name: 'Main' });
	await expect(nav.getByText('CaSSAndRA')).toBeVisible();
	await expect(nav.getByText(version)).toBeVisible();
	await expect(nav.getByRole('link', { name: 'Live' })).toHaveAttribute('aria-current', 'page');
});

test('client routes are served by the SPA fallback', async ({ request }) => {
	const res = await request.get('/some/client/route');

	expect(res.status()).toBe(200);
	expect(res.headers()['content-type']).toContain('text/html');
});
