// Settings as sent by the backend (settings/settings.go, settings/api.go).

export type LinkKind = 'sim' | 'http' | 'uart' | 'mqtt';
export type Pattern = 'lines' | 'squares' | 'rings';

export interface Connection {
	kind: LinkKind;
	httpUrl: string;
	httpPassword: number;
	uartPort: string;
	uartBaud: number;
	mqttBroker: string;
	mqttMower: string;
	mqttClientId: string;
	mqttUser: string;
	mqttPassword: string;
}

export interface Rover {
	mowSpeedMps: number;
	gotoSpeedMps: number;
	fixTimeoutSec: number;
	finishAndRestart: boolean;
	absolutePosition: boolean;
	lon: number;
	lat: number;
}

export interface Battery {
	emptyV: number;
	fullV: number;
	chargingBelowA: number;
	offlineAfterSec: number;
}

export interface Planner {
	pattern: Pattern;
	widthM: number;
	angleDeg: number;
	distanceToBorder: number;
	mowArea: boolean;
	borderLaps: number;
	mowExclusions: boolean;
	borderCcw: boolean;
}

export interface Api {
	enabled: boolean;
	broker: string;
	serverName: string;
	clientId: string;
	user: string;
	password: string;
}

/** Robot pictures in static/rovers, as in settings.RobotPictures. */
export const robotPictures = ['default', 'ardumower', 'alfred', 'landrumower'] as const;
export type RobotPictureName = (typeof robotPictures)[number];

export interface Appearance {
	robotPicture: RobotPictureName;
	/** Edge of the square picture on the map. */
	robotSizeCm: number;
}

export interface Settings {
	connection: Connection;
	rover: Rover;
	battery: Battery;
	planner: Planner;
	api: Api;
	appearance: Appearance;
}

/** Which passwords are set; the backend never sends them. */
export interface Secrets {
	httpPassword: boolean;
	mqttPassword: boolean;
	apiPassword: boolean;
}

export interface SettingsView {
	settings: Settings;
	secrets: Secrets;
}

/** Body of PUT /api/settings: a missing password stays as it is. */
export interface SettingsUpdate {
	settings: Settings;
	passwords: {
		httpPassword?: number;
		mqttPassword?: string;
		apiPassword?: string;
	};
}
