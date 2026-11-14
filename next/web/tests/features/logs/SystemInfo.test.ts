import { render, screen } from '@testing-library/svelte';
import { describe, expect, it, vi } from 'vitest';
import SystemInfo from '#features/logs/SystemInfo.svelte';

const value = (label: string) => screen.getByText(label).nextElementSibling?.textContent;

describe('SystemInfo', () => {
	it('shows the values with one decimal and a dash where there is none', async () => {
		const load = vi.fn(async () => ({
			cpuLoadPercent: 12.5,
			cpuTempC: null,
			memUsedPercent: 40,
			diskUsedPercent: 3.25
		}));
		render(SystemInfo, { load, refreshMs: 0 });
		await vi.waitFor(() => expect(value('CPU load')).toBe('12.5 %'));
		expect(value('CPU temperature')).toBe('–');
		expect(value('Memory used')).toBe('40.0 %');
		expect(load).toHaveBeenCalledTimes(1);
	});

	it('says why it cannot load', async () => {
		render(SystemInfo, {
			load: vi.fn(async () => Promise.reject(new Error('gone'))),
			refreshMs: 0
		});
		expect((await screen.findByRole('alert')).textContent).toContain('gone');
		expect(value('Disk used')).toBe('–');
	});
});
