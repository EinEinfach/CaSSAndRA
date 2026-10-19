import { expect, test, type Page } from '@playwright/test';

// Plans a route for part of a garden with the real C++ planner.

const button = (page: Page, name: string) => page.getByRole('button', { name, exact: true });

let previousActive = '';

test.beforeAll(async ({ request }) => {
	previousActive = (await (await request.get('/api/maps')).json()).activeId;
	const res = await request.post('/api/maps', {
		data: {
			name: `E2E tasks ${Date.now()}`,
			perimeter: [
				{ x: 0, y: 0 },
				{ x: 20, y: 0 },
				{ x: 20, y: 12 },
				{ x: 0, y: 12 }
			],
			exclusions: [
				[
					{ x: 8, y: 4 },
					{ x: 12, y: 4 },
					{ x: 12, y: 8 },
					{ x: 8, y: 8 }
				]
			]
		}
	});
	expect(res.status()).toBe(201);
	const { id } = await res.json();
	expect((await request.put('/api/maps/active', { data: { id } })).status()).toBe(204);
});

test.afterAll(async ({ request }) => {
	await request.delete('/api/tasks/preview');
	await request.put('/api/maps/active', { data: { id: previousActive } });
});

test('plan rings for a rectangle across an exclusion', async ({ page }) => {
	await page.goto('/tasks');
	await page.getByRole('radio', { name: 'Rectangle' }).check({ force: true });
	await expect(button(page, 'Calculate route')).toBeDisabled();

	const box = (await page.getByLabel('Map for planning a route').boundingBox())!;
	const at = (fx: number, fy: number) => [box.x + box.width * fx, box.y + box.height * fy] as const;
	await page.mouse.move(...at(0.15, 0.2));
	await page.mouse.down();
	await page.mouse.move(...at(0.35, 0.5), { steps: 5 });
	await page.mouse.move(...at(0.55, 0.8), { steps: 5 });
	await page.mouse.up();

	await page.getByRole('radio', { name: 'Rings' }).check({ force: true });
	await button(page, 'Calculate route').click();
	const result = page.getByLabel('Planned route');
	await expect(result).toContainText(/\d+ points/, { timeout: 15_000 });
	await expect(page.getByText(/changed since/)).toHaveCount(0);

	// Every browser sees the plan; a new page shows it again.
	await page.reload();
	await expect(page.getByLabel('Planned route')).toContainText(/\d+ points/);
	await expect(page.getByRole('radio', { name: 'Rings' })).toBeChecked();

	await button(page, 'Discard route').click();
	await expect(page.getByLabel('Planned route')).toHaveCount(0);
});
