import { render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import Chart from '#features/stats/Chart.svelte';
import { sample } from './fixtures.ts';

beforeEach(() => {
	vi.stubGlobal(
		'ResizeObserver',
		class {
			observe() {}
			unobserve() {}
			disconnect() {}
		}
	);
});
afterEach(() => vi.unstubAllGlobals());

const span = { from: new Date('2026-10-26T08:00:00Z'), to: new Date('2026-10-26T09:00:00Z') };

describe('Chart', () => {
	it('draws the line with a round axis and names the latest value', () => {
		render(Chart, {
			title: 'Battery',
			unit: 'V',
			samples: [
				sample('2026-10-26T08:00:00Z', { batteryV: 23.4 }),
				sample('2026-10-26T08:30:00Z', { batteryV: 28.1 })
			],
			value: (s) => s.batteryV,
			...span,
			digits: 2
		});
		const svg = screen.getByRole('img', { name: 'Battery over time' });
		expect(svg.querySelector('path')!.getAttribute('d')).toMatch(/^M[\d.]+,[\d.]+L[\d.]+,[\d.]+$/);
		expect([...svg.querySelectorAll('text')].map((t) => t.textContent)).toEqual([
			'22',
			'24',
			'26',
			'28',
			'30'
		]);
		expect(screen.getByText('28.10 V')).toBeTruthy();
	});

	it('says when there is nothing to draw', () => {
		render(Chart, { title: 'Current', unit: 'A', samples: [], value: (s) => s.amps, ...span });
		expect(screen.getByText('No data in this time span.')).toBeTruthy();
		expect(screen.queryByRole('img')).toBeNull();
	});
});
