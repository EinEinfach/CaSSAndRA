import { describe, expect, it } from 'vitest';
import { commandProblem, normalizeCommand } from '#features/logs/command.ts';

describe('commandProblem', () => {
	it.each([
		['', ''],
		['AT+V', ''],
		['  at+s  ', ''],
		['AT+C,0,0,-1,-1,-1,-1,-1,-1', ''],
		['V', 'Commands start with AT+, e.g. AT+V.'],
		['AT+', 'Commands start with AT+, e.g. AT+V.'],
		['AT+' + 'x'.repeat(198), 'At most 200 characters.'],
		['AT+Vä', 'Only plain ASCII characters.']
	])('%j', (line, want) => {
		expect(commandProblem(line)).toBe(want);
	});
});

describe('normalizeCommand', () => {
	it('writes the prefix in upper case and trims', () => {
		expect(normalizeCommand('  at+V ')).toBe('AT+V');
		expect(normalizeCommand('At+c,0,4')).toBe('AT+c,0,4');
	});
});
