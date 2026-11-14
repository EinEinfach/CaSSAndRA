import { describe, expect, it, vi } from 'vitest';
import { fetchLogs, fetchSystem, sendCommand } from '#features/logs/api.ts';

const json = (body: unknown, status = 200) =>
	vi.fn(async () => new Response(JSON.stringify(body), { status }));

describe('logs api', () => {
	it('asks for the records after a seq', async () => {
		const fetchFn = json({
			entries: [{ seq: 8, time: '2026-11-14T10:00:00Z', level: 'INFO', message: 'hi' }]
		});
		const got = await fetchLogs(7, fetchFn);
		expect(got.map((e) => e.seq)).toEqual([8]);
		expect(fetchFn).toHaveBeenCalledWith('/api/logs?after=7', expect.anything());
	});

	it('sends a command and returns the reply', async () => {
		const fetchFn = json({ reply: 'V,Ardumower Sunray,1.0.324,1,52,0x26' });
		await expect(sendCommand('AT+V', fetchFn)).resolves.toBe(
			'V,Ardumower Sunray,1.0.324,1,52,0x26'
		);
		expect(fetchFn).toHaveBeenCalledWith(
			'/api/robot/raw',
			expect.objectContaining({ method: 'POST', body: '{"line":"AT+V"}' })
		);
	});

	it('reports why a command was refused', async () => {
		const fetchFn = json({ error: 'robot is offline' }, 503);
		await expect(sendCommand('AT+V', fetchFn)).rejects.toThrow('robot is offline');
	});

	it('reads the system info', async () => {
		const fetchFn = json({
			cpuLoadPercent: 12.5,
			cpuTempC: null,
			memUsedPercent: 40,
			diskUsedPercent: 3
		});
		await expect(fetchSystem(fetchFn)).resolves.toMatchObject({
			cpuLoadPercent: 12.5,
			cpuTempC: null
		});
		expect(fetchFn).toHaveBeenCalledWith('/api/system', expect.anything());
	});
});
