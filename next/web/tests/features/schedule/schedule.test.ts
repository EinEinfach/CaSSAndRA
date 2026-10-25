import { describe, expect, it } from 'vitest';
import {
	clock,
	describe as describeStatus,
	formatNext,
	isDayOff,
	isDirty,
	minutes,
	setDayOn,
	setStart,
	timeOptions
} from '#features/schedule/schedule.ts';
import { dayOff, schedule } from './fixtures.ts';

const day = (start: string, end: string) => ({ start, end, taskIds: ['a'] });

describe('schedule helpers', () => {
	it('converts between "HH:MM" and minutes', () => {
		expect(minutes('09:30')).toBe(570);
		expect(minutes('24:00')).toBe(1440);
		expect(clock(570)).toBe('09:30');
		expect(clock(1440)).toBe('24:00');
	});

	it('offers every quarter hour and keeps a time off that grid', () => {
		const grid = timeOptions('09:00');
		expect(grid).toHaveLength(97);
		expect(grid[0]).toBe('00:00');
		expect(grid.at(-1)).toBe('24:00');
		const odd = timeOptions('07:20');
		expect(odd).toHaveLength(98);
		expect(odd.indexOf('07:20')).toBe(odd.indexOf('07:15') + 1);
	});

	it('switches a day on with a three-hour window and off again', () => {
		expect(isDayOff(dayOff())).toBe(true);
		expect(setDayOn(dayOff(), true)).toEqual({ start: '12:00', end: '15:00', taskIds: [] });
		expect(setDayOn(day('22:00', '22:00'), true)).toMatchObject({ start: '22:00', end: '24:00' });
		expect(setDayOn(day('24:00', '24:00'), true)).toMatchObject({ start: '21:00', end: '24:00' });
		expect(setDayOn(day('09:00', '12:00'), false)).toMatchObject({ start: '09:00', end: '09:00' });
		expect(setDayOn(day('09:00', '12:00'), false).taskIds).toEqual(['a']);
	});

	it('keeps the end when the start moves, unless the start passes it', () => {
		expect(setStart(day('09:00', '12:00'), '10:00')).toMatchObject({
			start: '10:00',
			end: '12:00'
		});
		expect(setStart(day('09:00', '12:00'), '13:00')).toMatchObject({
			start: '13:00',
			end: '16:00'
		});
		expect(setStart(day('09:00', '12:00'), '23:00')).toMatchObject({
			start: '23:00',
			end: '24:00'
		});
	});

	it('notices changes', () => {
		const a = schedule();
		const b = structuredClone(a);
		expect(isDirty(a, b)).toBe(false);
		b.days[3].taskIds.push('x');
		expect(isDirty(a, b)).toBe(true);
	});

	it('tells when the next start is', () => {
		const now = new Date(2026, 9, 26, 8, 0); // Monday 08:00 local time
		const at = (d: number, h: number, m = 0) => new Date(2026, 9, d, h, m).toISOString();
		expect(formatNext('', now)).toBe('');
		expect(formatNext(at(26, 8), now)).toBe('now');
		expect(formatNext(at(26, 9), now)).toBe('today 09:00');
		expect(formatNext(at(27, 7, 30), now)).toBe('tomorrow 07:30');
		expect(formatNext(at(28, 7, 30), now)).toBe('Wed 07:30');
	});

	it('describes the status in one line', () => {
		const now = new Date(2026, 9, 26, 8, 0);
		const next = new Date(2026, 9, 26, 9, 0).toISOString();
		expect(describeStatus({ state: 'off', message: 'the schedule is off', next: '' }, now)).toBe(
			'The schedule is off.'
		);
		expect(describeStatus({ state: 'waiting', message: '', next }, now)).toBe(
			'Next start: today 09:00.'
		);
		expect(
			describeStatus({ state: 'started', message: 'mowing 2 tasks until 12:00', next: '' }, now)
		).toBe('Mowing 2 tasks until 12:00.');
		expect(describeStatus({ state: 'waiting', message: '', next: '' }, now)).toBe(
			'No window planned.'
		);
	});
});
