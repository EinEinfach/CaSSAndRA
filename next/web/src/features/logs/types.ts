// Types of the log view API (logs/logs.go, robot/api.go, system/system.go).

export type Level = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';

export interface LogEntry {
	/** Increases by one per record. */
	seq: number;
	time: string;
	level: Level;
	/** Message with its attributes as key=value. */
	message: string;
}

export interface LogList {
	entries: LogEntry[];
}

/** Values are null where the computer does not report them (not Linux). */
export interface SystemInfo {
	cpuLoadPercent: number | null;
	cpuTempC: number | null;
	memUsedPercent: number | null;
	diskUsedPercent: number | null;
}
