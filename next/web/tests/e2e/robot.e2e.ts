import { expect, test, type Page } from '@playwright/test';

// Runs against the built binary with the simulated robot and its demo garden.

const status = (page: Page) => page.getByTestId('robot-status');
const button = (page: Page, name: string) => page.getByRole('button', { name, exact: true });

async function robotPosition(page: Page): Promise<{ x: number; y: number }> {
	const res = await page.request.get('/api/robot/state');
	return (await res.json()).position;
}

test('mow, stop and dock the simulated robot', async ({ page }) => {
	await page.goto('/');

	await expect(page.getByLabel('Garden map with robot position')).toBeVisible();
	await expect(status(page)).toHaveText(/Idle|Docked|Charging/, { timeout: 10_000 });
	await expect(page.getByTestId('robot-battery')).toContainText('%');

	await button(page, 'Mow').click();
	await expect(status(page)).toHaveText('Mowing');
	await expect(button(page, 'Mow')).toBeDisabled();

	const start = await robotPosition(page);
	await expect.poll(async () => robotPosition(page), { timeout: 5_000 }).not.toEqual(start);

	await button(page, 'Stop').click();
	await expect(status(page)).toHaveText('Idle');

	await button(page, 'Dock').click();
	await expect(status(page)).toHaveText('Docking');
	await expect(page.getByText('sent home by you')).toBeVisible();
});

test('the joystick drives the robot', async ({ page }) => {
	await page.goto('/');
	await button(page, 'Stop').click();
	await expect(status(page)).toHaveText('Idle', { timeout: 10_000 });

	const pad = page.getByRole('slider');
	const box = (await pad.boundingBox())!;
	const start = await robotPosition(page);

	await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
	await page.mouse.down();
	await page.mouse.move(box.x + box.width / 2, box.y + 10, { steps: 5 });
	await expect(status(page)).toHaveText('Manual drive');
	await expect.poll(async () => robotPosition(page), { timeout: 5_000 }).not.toEqual(start);
	await page.mouse.up();

	await expect(status(page)).toHaveText('Idle', { timeout: 5_000 });
});

test('the joystick drives the robot off the dock', async ({ page }) => {
	await page.goto('/');
	await button(page, 'Dock').click();
	await expect(status(page)).toHaveText('Charging', { timeout: 30_000 });

	const pad = page.getByRole('slider');
	const box = (await pad.boundingBox())!;
	const start = await robotPosition(page);
	await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
	await page.mouse.down();
	await page.mouse.move(box.x + box.width / 2, box.y + box.height - 10, { steps: 5 });
	await expect.poll(async () => robotPosition(page), { timeout: 5_000 }).not.toEqual(start);
	await page.mouse.up();

	await expect(status(page)).toHaveText('Idle', { timeout: 5_000 });
});

// The server sends the robot state only when it changes; a page opened again
// must still show it (the shared stream replays the latest events).
test('the live view keeps its data after visiting another page', async ({ page }) => {
	await page.goto('/');
	await expect(status(page)).toHaveText(/Idle|Docked|Charging/, { timeout: 10_000 });
	const before = await status(page).textContent();

	await page.getByRole('link', { name: 'Maps' }).click();
	await expect(page).toHaveURL(/\/maps/);
	await page.getByRole('link', { name: 'Live' }).click();

	await expect(status(page)).toHaveText(before!, { timeout: 1_000 });
	await expect(page.getByTestId('robot-battery')).toContainText('%');
});

test('the trail starts anew when the robot docks or is cleared', async ({ page }) => {
	const clear = page.getByRole('button', { name: 'Clear trail' });
	await page.goto('/');
	await expect(status(page)).toHaveText(/Idle|Docked|Charging/, { timeout: 10_000 });

	await button(page, 'Mow').click();
	await expect(clear).toBeVisible({ timeout: 5_000 });
	await clear.click();
	await expect(clear).toBeHidden();
	await expect(clear).toBeVisible({ timeout: 5_000 }); // grows again while mowing

	await button(page, 'Dock').click();
	await expect(status(page)).toHaveText('Charging', { timeout: 30_000 });
	await expect(clear).toBeHidden();
	const trail = await (await page.request.get('/api/robot/trail')).json();
	expect(trail.points.length).toBeLessThanOrEqual(1);
});
