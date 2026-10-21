import { expect, test, type Page } from '@playwright/test';

// Draws a map in the editor, saves it and sends it to the simulated robot.

const button = (page: Page, name: string) => page.getByRole('button', { name, exact: true });

/** Clicks the editor canvas at a fraction of its size. */
async function clickCanvas(page: Page, fx: number, fy: number) {
	const box = (await page.getByLabel('Map editor canvas').boundingBox())!;
	await page.mouse.click(box.x + box.width * fx, box.y + box.height * fy);
}

let previousActive = '';

test.beforeAll(async ({ request }) => {
	previousActive = (await (await request.get('/api/maps')).json()).activeId;
});

test.afterAll(async ({ request }) => {
	// The simulator starts with the active map: give the others the demo garden back.
	await request.put('/api/maps/active', { data: { id: previousActive } });
	// Reconnecting starts a fresh simulator with the demo garden for the other tests.
	await request.put('/api/settings', { data: { settings: { connection: { kind: 'uart' } } } });
	await request.put('/api/settings', { data: { settings: { connection: { kind: 'sim' } } } });
});

test('draw a map, save it and send it to the robot', async ({ page }) => {
	const name = `E2E garden ${Date.now()}`;
	await page.goto('/maps');
	await expect(page.getByRole('heading', { name: 'Maps' })).toBeVisible();

	await button(page, '+ New map').click();
	await page.getByLabel('Map name').fill(name);
	for (const [fx, fy] of [
		[0.3, 0.3],
		[0.7, 0.3],
		[0.7, 0.6],
		[0.3, 0.6]
	]) {
		await clickCanvas(page, fx, fy);
	}
	await expect(page.getByRole('tab', { name: /Perimeter/ })).toContainText('4');

	await page.getByRole('tab', { name: /Dock path/ }).click();
	await clickCanvas(page, 0.4, 0.5);
	await clickCanvas(page, 0.45, 0.5);
	await button(page, 'Save map').click();

	const detail = page.getByRole('region', { name });
	await expect(detail.getByRole('heading', { name })).toBeVisible();
	await button(page, 'Send to robot').click();
	await expect(page.getByRole('status')).toHaveText('Sent to the robot.', { timeout: 15_000 });
	await expect(page.getByRole('list', { name: 'Maps' }).getByText('On robot')).toBeVisible();

	// The live view shows the map the robot has now.
	await page.getByRole('link', { name: 'Live' }).click();
	await expect(page.getByLabel('Garden map with robot position')).toBeVisible();
});

test('a map that is not valid cannot be saved', async ({ page }) => {
	await page.goto('/maps');
	await button(page, '+ New map').click();
	await expect(button(page, 'Save map')).toBeDisabled();
	await expect(page.getByText('The perimeter needs at least 3 points.')).toBeVisible();
	await button(page, 'Cancel').click();
	await expect(page.getByRole('heading', { name: 'Maps' })).toBeVisible();
});
