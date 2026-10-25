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
	/** Publish to the built-in broker; broker, user and password are not used then. */
	useBuiltinBroker: boolean;
}

/** The MQTT broker built into CaSSAndRA, for users without one. */
export interface Broker {
	enabled: boolean;
	port: number;
	user: string;
	password: string;
}

export type NotifyService = '' | 'telegram' | 'pushover';

/** Messages when the robot goes offline or reports an error. */
export interface Notify {
	service: NotifyService;
	telegramToken: string;
	/** Found from the bot's last message when empty. */
	telegramChatId: string;
	pushoverToken: string;
	pushoverUser: string;
}

/** GET /api/broker */
export interface BrokerStatus {
	enabled: boolean;
	running: boolean;
	port: number;
	/** Connected now, CaSSAndRA's own API included. */
	clients: number;
	/** Why it does not run, e.g. the port is taken. */
	error: string;
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
	broker: Broker;
	notify: Notify;
	appearance: Appearance;
}

/** Which passwords are set; the backend never sends them. */
export interface Secrets {
	httpPassword: boolean;
	mqttPassword: boolean;
	apiPassword: boolean;
	brokerPassword: boolean;
	telegramToken: boolean;
	pushoverToken: boolean;
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
		brokerPassword?: string;
		telegramToken?: string;
		pushoverToken?: string;
	};
}
