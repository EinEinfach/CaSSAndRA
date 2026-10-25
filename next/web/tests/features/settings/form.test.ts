import { describe, expect, it } from 'vitest';
import { emptyEdits, isDirty, passwordUpdate } from '#features/settings/form.ts';
import { view } from './fixtures.ts';

describe('passwordUpdate', () => {
	it('keeps every password when nothing was typed', () => {
		expect(passwordUpdate(emptyEdits())).toEqual({});
	});

	it('sets typed passwords and removes on request', () => {
		const e = emptyEdits();
		e.httpPassword.value = ' 4711 ';
		e.mqttPassword.value = 'secret';
		e.apiPassword = { value: 'ignored', remove: true };
		e.brokerPassword.value = 'mow-the-lawn';
		expect(passwordUpdate(e)).toEqual({
			httpPassword: 4711,
			mqttPassword: 'secret',
			apiPassword: '',
			brokerPassword: 'mow-the-lawn'
		});
	});

	it('removes the robot password with 0', () => {
		const e = emptyEdits();
		e.httpPassword.remove = true;
		expect(passwordUpdate(e)).toEqual({ httpPassword: 0 });
	});

	it('rejects a robot password that is not a number', () => {
		const e = emptyEdits();
		e.httpPassword.value = 'abc';
		expect(() => passwordUpdate(e)).toThrow('must be a number');
	});
});

describe('isDirty', () => {
	it('is clean for the saved settings', () => {
		expect(isDirty(view().settings, view().settings, emptyEdits())).toBe(false);
	});

	it('notices a changed field', () => {
		const draft = view().settings;
		draft.rover.mowSpeedMps = 0.3;
		expect(isDirty(view().settings, draft, emptyEdits())).toBe(true);
	});

	it('notices a typed or removed password', () => {
		const typed = emptyEdits();
		typed.mqttPassword.value = 'x';
		const removed = emptyEdits();
		removed.httpPassword.remove = true;
		expect(isDirty(view().settings, view().settings, typed)).toBe(true);
		expect(isDirty(view().settings, view().settings, removed)).toBe(true);
	});
});
