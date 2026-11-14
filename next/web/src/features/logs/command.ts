// Checks a typed robot command before it is sent (the backend checks again).

export const MAX_COMMAND_LENGTH = 200;

/** What is wrong with the line, or '' if it can be sent. */
export function commandProblem(line: string): string {
	const l = line.trim();
	if (l === '') return '';
	if (!/^AT\+./i.test(l)) return 'Commands start with AT+, e.g. AT+V.';
	if (l.length > MAX_COMMAND_LENGTH) return `At most ${MAX_COMMAND_LENGTH} characters.`;
	if (!/^[\x20-\x7e]+$/.test(l)) return 'Only plain ASCII characters.';
	return '';
}

/** The firmware wants upper case "AT+"; the rest stays as typed. */
export function normalizeCommand(line: string): string {
	const l = line.trim();
	return /^at\+/i.test(l) ? 'AT+' + l.slice(3) : l;
}
