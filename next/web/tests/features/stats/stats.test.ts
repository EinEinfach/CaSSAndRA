import { describe, expect, it } from 'vitest';
import {
	formatDistance,
	formatDuration,
	linePath,
	niceScale,
	percent,
	shares,
	span,
	timeLabel
} from '#features/stats/stats.ts';
import { sample } from './fixtures.ts';

describe('stats helpers', () => {
	it('spans a range up to now', () => {
		const now = new Date('2026-10-26T12:00:00Z');
		expect(span('day', now).from.toISOString()).toBe('2026-10-25T12:00:00.000Z');
		expect(span('week', now).from.toISOString()).toBe('2026-10-19T12:00:00.000Z');
		expect(span('year', now).to).toBe(now);
	});

	it('splits totals into shares', () => {
		const got = shares({ a: 30, b: 10 }, [
			{ key: 'a', label: 'A' },
			{ key: 'b', label: 'B' },
			{ key: 'c', label: 'C' }
		]);
		expect(got.map((s) => s.part)).toEqual([0.75, 0.25, 0]);
		expect(shares({}, [{ key: 'a', label: 'A' }])[0].part).toBe(0);
	});

	it('formats durations, distances and shares', () => {
		expect(formatDuration(0)).toBe('0 min');
		expect(formatDuration(45 * 60)).toBe('45 min');
		expect(formatDuration(3 * 3600)).toBe('3 h');
		expect(formatDuration(3 * 3600 + 20 * 60)).toBe('3 h 20 min');
		expect(formatDuration(250 * 3600 + 60)).toBe('250 h');
		expect(formatDistance(849.6)).toBe('850 m');
		expect(formatDistance(12_440)).toBe('12.4 km');
		expect(percent(0.756)).toBe('76 %');
	});

	it('draws a line over time and breaks it where samples are missing', () => {
		const t = (min: number) => new Date(Date.UTC(2026, 9, 26, 8, min)).toISOString();
		const box = {
			from: Date.parse(t(0)),
			to: Date.parse(t(100)),
			min: 0,
			max: 10,
			width: 100,
			height: 10
		};
		const samples = [0, 1, 2, 50, 51].map((m) => sample(t(m), { batteryV: m % 10 }));
		expect(linePath(samples, (s) => s.batteryV, box)).toBe(
			'M0.0,10.0L1.0,9.0L2.0,8.0M50.0,10.0L51.0,9.0'
		);
		expect(linePath([], (s) => s.batteryV, box)).toBe('');
	});

	it('labels the time axis by the length of the span', () => {
		const d = new Date(2026, 9, 26, 9, 5);
		expect(timeLabel(d, 24 * 3_600_000)).toBe('Mon 09:05');
		expect(timeLabel(d, 7 * 24 * 3_600_000)).toBe('26 Oct');
	});

	it('finds a round scale around the values', () => {
		expect(niceScale([23.4, 28.1])).toEqual({ min: 22, max: 30, ticks: [22, 24, 26, 28, 30] });
		expect(niceScale([5, 5])).toEqual({ min: 4, max: 6, ticks: [4, 4.5, 5, 5.5, 6] });
		expect(niceScale([])).toEqual({ min: 0, max: 1, ticks: [0, 1] });
	});
});
