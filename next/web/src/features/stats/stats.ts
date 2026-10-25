// Pure helpers for the stats page: ranges, shares, numbers and chart paths.
import type { RangeName, Sample } from './types.ts';

const hour = 3_600_000;

export const ranges: { name: RangeName; label: string; ms: number }[] = [
	{ name: 'day', label: '24 h', ms: 24 * hour },
	{ name: 'week', label: '7 days', ms: 7 * 24 * hour },
	{ name: 'month', label: '30 days', ms: 30 * 24 * hour },
	{ name: 'year', label: '1 year', ms: 365 * 24 * hour }
];

/** The time span of a range up to now. */
export function span(name: RangeName, now: Date): { from: Date; to: Date } {
	const r = ranges.find((x) => x.name === name)!;
	return { from: new Date(now.getTime() - r.ms), to: now };
}

export interface Share {
	key: string;
	label: string;
	seconds: number;
	/** 0..1 of the sum of all shares */
	part: number;
}

/** How a total splits into parts, e.g. mow, charge and idle time. */
export function shares(
	totals: Record<string, number>,
	parts: { key: string; label: string }[]
): Share[] {
	const sum = parts.reduce((s, p) => s + (totals[p.key] ?? 0), 0);
	return parts.map((p) => {
		const seconds = totals[p.key] ?? 0;
		return { ...p, seconds, part: sum > 0 ? seconds / sum : 0 };
	});
}

/** A duration as "3 h 20 min", "45 min" or "0 min". */
export function formatDuration(seconds: number): string {
	const min = Math.round(seconds / 60);
	const h = Math.floor(min / 60);
	if (h === 0) return `${min} min`;
	if (h >= 100) return `${h} h`;
	return min % 60 === 0 ? `${h} h` : `${h} h ${min % 60} min`;
}

/** A distance as "850 m" or "12.4 km". */
export function formatDistance(m: number): string {
	return m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`;
}

export const percent = (part: number) => `${Math.round(part * 100)} %`;

export interface Box {
	from: number; // ms
	to: number;
	min: number;
	max: number;
	width: number;
	height: number;
}

/**
 * The SVG path of value over time. The line breaks where samples are missing
 * (a gap of more than three times the usual distance, e.g. the robot was off).
 */
export function linePath(samples: Sample[], value: (s: Sample) => number, box: Box): string {
	if (samples.length === 0) return '';
	const ts = samples.map((s) => Date.parse(s.t));
	const steps = ts.slice(1).map((t, i) => t - ts[i]);
	const usual = steps.length ? [...steps].sort((a, b) => a - b)[Math.floor(steps.length / 2)] : 0;
	const x = (t: number) => ((t - box.from) / (box.to - box.from)) * box.width;
	const range = box.max - box.min || 1;
	const y = (v: number) => box.height - ((v - box.min) / range) * box.height;
	return samples
		.map((s, i) => {
			const gap = i > 0 && ts[i] - ts[i - 1] > 3 * usual;
			return `${i === 0 || gap ? 'M' : 'L'}${x(ts[i]).toFixed(1)},${y(value(s)).toFixed(1)}`;
		})
		.join('');
}

/** A value range around the data with round ends, and its tick values. */
export function niceScale(
	values: number[],
	ticks = 4
): { min: number; max: number; ticks: number[] } {
	if (values.length === 0) return { min: 0, max: 1, ticks: [0, 1] };
	let lo = Math.min(...values);
	let hi = Math.max(...values);
	if (lo === hi) {
		lo -= 1;
		hi += 1;
	}
	const raw = (hi - lo) / ticks;
	const mag = 10 ** Math.floor(Math.log10(raw));
	const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw)!;
	const min = Math.floor(lo / step) * step;
	const max = Math.ceil(hi / step) * step;
	const out: number[] = [];
	for (let v = min; v <= max + step / 2; v += step) out.push(Number(v.toFixed(10)));
	return { min, max, ticks: out };
}

const shortTime = new Intl.DateTimeFormat('en-GB', {
	weekday: 'short',
	hour: '2-digit',
	minute: '2-digit'
});
const shortDate = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' });

/** A label on the time axis: weekday and time for spans up to two days, else the date. */
export function timeLabel(d: Date, spanMs: number): string {
	return spanMs <= 2 * 24 * hour ? shortTime.format(d) : shortDate.format(d);
}
