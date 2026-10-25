// Types of the stats API (stats/api.go).

export interface Sample {
	/** RFC 3339 */
	t: string;
	batteryV: number;
	amps: number;
	satellites: number;
	accuracyM: number;
	lateralErrorM: number;
}

/** GET /api/stats */
export interface StatsResponse {
	from: string;
	to: string;
	samples: Sample[];
	/** Growth of the firmware counters in whole hours (…Sec, distanceMowM, obstacles …) and the maxima (max…). */
	totals: Record<string, number>;
}

export type RangeName = 'day' | 'week' | 'month' | 'year';
