import type { SettingsView } from '#features/settings/types.ts';

export function view(): SettingsView {
	return {
		settings: {
			connection: {
				kind: 'http',
				httpUrl: 'http://192.168.1.50',
				httpPassword: 0,
				uartPort: '/dev/ttyACM0',
				uartBaud: 115200,
				mqttBroker: '',
				mqttMower: 'Ardumower',
				mqttClientId: 'CaSSAndRA',
				mqttUser: '',
				mqttPassword: ''
			},
			rover: {
				mowSpeedMps: 0.25,
				gotoSpeedMps: 0.3,
				fixTimeoutSec: 60,
				finishAndRestart: false,
				absolutePosition: false,
				lon: 0,
				lat: 0
			},
			battery: { emptyV: 22, fullV: 28, chargingBelowA: -0.03, offlineAfterSec: 60 },
			planner: {
				pattern: 'lines',
				widthM: 0.18,
				angleDeg: 0,
				distanceToBorder: 1,
				mowArea: true,
				borderLaps: 1,
				mowExclusions: true,
				borderCcw: false
			},
			api: {
				enabled: false,
				broker: '',
				serverName: 'CaSSAndRA',
				clientId: 'CaSSAndRA-API',
				user: '',
				password: ''
			},
			appearance: { robotPicture: 'default', robotSizeCm: 100 }
		},
		secrets: { httpPassword: true, mqttPassword: false, apiPassword: false }
	};
}
