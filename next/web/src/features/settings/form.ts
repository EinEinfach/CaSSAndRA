// Logic of the settings form. The backend never sends passwords, so an
// empty password field means "keep"; removing one is an explicit choice.
import type { Secrets, Settings, SettingsUpdate } from './types.ts';

export interface PasswordEdit {
	value: string;
	remove: boolean;
}

export type PasswordEdits = Record<keyof Secrets, PasswordEdit>;

export const emptyEdits = (): PasswordEdits => ({
	httpPassword: { value: '', remove: false },
	mqttPassword: { value: '', remove: false },
	apiPassword: { value: '', remove: false },
	brokerPassword: { value: '', remove: false }
});

/** The password part of the update. Throws if the HTTP password is not a number. */
export function passwordUpdate(edits: PasswordEdits): SettingsUpdate['passwords'] {
	const out: SettingsUpdate['passwords'] = {};
	const http = edits.httpPassword;
	if (http.remove) {
		out.httpPassword = 0;
	} else if (http.value.trim() !== '') {
		if (!/^\d+$/.test(http.value.trim())) {
			throw new Error('The robot password must be a number (see config.h of the firmware).');
		}
		out.httpPassword = Number(http.value.trim());
	}
	for (const key of ['mqttPassword', 'apiPassword', 'brokerPassword'] as const) {
		const e = edits[key];
		if (e.remove) out[key] = '';
		else if (e.value !== '') out[key] = e.value;
	}
	return out;
}

/** Whether the form differs from the saved settings. */
export function isDirty(saved: Settings, draft: Settings, edits: PasswordEdits): boolean {
	const passwordsTouched = Object.values(edits).some((e) => e.remove || e.value !== '');
	return passwordsTouched || JSON.stringify(saved) !== JSON.stringify(draft);
}
