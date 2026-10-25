import type { Sample, StatsResponse } from '#features/stats/types.ts';

export function sample(t: string, overrides: Partial<Sample> = {}): Sample {
	return {
		t,
		batteryV: 27,
		amps: 0.5,
		satellites: 30,
		accuracyM: 0.02,
		lateralErrorM: 0.01,
		...overrides
	};
}

export function response(overrides: Partial<StatsResponse> = {}): StatsResponse {
	return {
		from: '2026-10-25T09:00:00Z',
		to: '2026-10-26T09:00:00Z',
		samples: [sample('2026-10-26T08:00:00Z'), sample('2026-10-26T08:05:00Z', { batteryV: 26.5 })],
		totals: {
			mowSec: 7200,
			chargeSec: 3600,
			idleSec: 0,
			mowFixSec: 6600,
			mowFloatSec: 600,
			mowInvalidSec: 0,
			distanceMowM: 2450,
			obstacles: 3,
			bumper: 1,
			maxCycleTimeSec: 0.123,
			maxDgpsAgeSec: 1.5
		},
		...overrides
	};
}
