import { expect, test, type Page } from '@playwright/test';

// Plans a route for part of a garden with the real C++ planner and mows it
// with the simulated robot.

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
			],
			// ends at the simulator's station, so the robot leaves along it
			dock: [
				{ x: 1, y: 3 },
				{ x: -1, y: 3 }
			]
		}
	});
	expect(res.status()).toBe(201);
	const { id } = await res.json();
	expect((await request.put('/api/maps/active', { data: { id } })).status()).toBe(204);
});

test.afterAll(async ({ request }) => {
	await request.post('/api/robot/stop');
	for (const t of (await (await request.get('/api/tasks')).json()).tasks) {
		await request.delete(`/api/tasks/${t.id}`);
	}
	await request.delete('/api/tasks/preview');
	await request.put('/api/maps/active', { data: { id: previousActive } });
	// Reconnecting starts a fresh simulator with the demo garden for the other tests.
	await request.put('/api/settings', { data: { settings: { connection: { kind: 'uart' } } } });
	await request.put('/api/settings', { data: { settings: { connection: { kind: 'sim' } } } });
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

test('start mowing the planned route, follow and jump ahead', async ({ page }) => {
	await page.goto('/tasks');
	await expect(page.getByRole('radio', { name: 'Whole garden' })).toBeChecked();
	await button(page, 'Calculate route').click();
	await expect(page.getByLabel('Planned route')).toContainText(/\d+ points/, { timeout: 15_000 });

	await button(page, 'Start mowing').click();
	await expect(page).toHaveURL(/\/$/, { timeout: 20_000 });
	await expect(page.getByTestId('robot-status')).toHaveText('Mowing', { timeout: 10_000 });
	const progress = page.getByTestId('route-progress');
	await expect(progress).toHaveText(/^\d+ %$/);

	await page.getByLabel('Jump to progress').fill('60');
	await button(page, 'Jump').click();
	await expect
		.poll(async () => parseInt((await progress.textContent()) ?? '0'), { timeout: 10_000 })
		.toBeGreaterThanOrEqual(60);

	await button(page, 'Stop').click();
	await expect(page.getByTestId('robot-status')).toHaveText('Idle', { timeout: 10_000 });
	await expect(page.getByLabel('Route progress')).toHaveCount(0);
});

test('save tasks, plan two of them in order and delete one', async ({ page }) => {
	await page.goto('/tasks');
	await expect(page.getByText(/No saved tasks/)).toBeVisible();

	for (const [name, pattern] of [
		['E2E lines', 'Lines'],
		['E2E rings', 'Rings']
	] as const) {
		await page.getByRole('radio', { name: pattern }).check({ force: true });
		await page.getByLabel('Task name').fill(name);
		await button(page, 'Save task').click();
		await expect(page.getByRole('status')).toHaveText(`Saved ${name}.`);
	}
	const list = page.getByRole('list', { name: 'Saved tasks' });
	await expect(list.getByRole('listitem')).toHaveCount(2);

	// The checkbox is hidden behind the order badge: tap the task's name.
	await list.getByText('E2E rings', { exact: true }).click();
	await list.getByText('E2E lines', { exact: true }).click();
	await button(page, 'Plan 2 tasks').click();
	await expect(page.getByLabel('Planned route')).toContainText(/\d+ points/, { timeout: 15_000 });

	// The choice survives a reload together with the plan.
	await page.reload();
	await expect(page.getByLabel('Mow E2E rings')).toBeChecked();
	await expect(page.getByText(/changed since/)).toHaveCount(0);

	await button(page, 'Delete E2E lines').click();
	await button(page, 'Delete E2E lines?').click();
	await expect(list.getByRole('listitem')).toHaveCount(1);
	await expect(page.getByText(/changed since/)).toBeVisible();
});

test('go to a point picked on the live map', async ({ page }) => {
	await page.goto('/');
	await expect(page.getByTestId('robot-status')).toHaveText(/Idle|Docked|Charging/, {
		timeout: 10_000
	});
	await button(page, 'Go to a point').click();
	await expect(page.getByRole('status').filter({ hasText: 'Tap the map' })).toBeVisible();

	const box = (await page.getByLabel('Garden map with robot position').boundingBox())!;
	await page.mouse.click(box.x + box.width * 0.3, box.y + box.height * 0.5);
	await expect(page.getByRole('status').filter({ hasText: 'Drive to' })).toBeVisible();
	await button(page, 'Drive there').click();

	await expect(page.getByTestId('robot-status')).toHaveText('Driving', { timeout: 15_000 });
	await expect(button(page, 'Go to a point')).toBeDisabled();
	await button(page, 'Stop').click();
	await expect(page.getByTestId('robot-status')).toHaveText('Idle', { timeout: 10_000 });
});
