// Enforces the frontend structure rules from CLAUDE.md: tests mirror the
// feature folders, no tests inside src/, shared code never depends on features.
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { describe, expect, it } from 'vitest';

const root = join(import.meta.dirname, '..');
const src = join(root, 'src');
const tests = join(root, 'tests');

function dirs(path: string): string[] {
	return readdirSync(path).filter((name) => statSync(join(path, name)).isDirectory());
}

function files(path: string): string[] {
	return readdirSync(path, { recursive: true, encoding: 'utf8' })
		.map((name) => join(path, name))
		.filter((file) => statSync(file).isFile());
}

const features = dirs(join(src, 'features'));
const testedFeatures = dirs(join(tests, 'features'));

describe('frontend architecture', () => {
	it('has features', () => {
		expect(features.length).toBeGreaterThan(0);
	});

	it.each(features)('feature %s has a mirrored tests folder', (feature) => {
		expect(testedFeatures).toContain(feature);
	});

	it.each(testedFeatures)('tests/features/%s mirrors a feature', (feature) => {
		expect(features).toContain(feature);
	});

	it('keeps tests out of src/', () => {
		const misplaced = files(src).filter((f) => /\.(test|spec|e2e)\.ts$/.test(f));
		expect(misplaced.map((f) => relative(root, f))).toEqual([]);
	});

	it('keeps shared/ independent of features', () => {
		const offenders = files(join(src, 'shared')).filter((f) =>
			readFileSync(f, 'utf8').includes('#features/')
		);
		expect(offenders.map((f) => relative(root, f))).toEqual([]);
	});

	it('mirrors shared/ code with tests', () => {
		const sources = files(join(src, 'shared'))
			.filter((f) => /\.(ts|svelte)$/.test(f))
			.map((f) => relative(join(src, 'shared'), f).replace(/(\.svelte)?\.ts$|\.svelte$/, ''));
		const tested = files(join(tests, 'shared')).map((f) =>
			relative(join(tests, 'shared'), f).replace(/\.test\.ts$/, '')
		);
		for (const source of sources) {
			expect(tested, `src/shared/${source} has no test`).toContain(source);
		}
	});
});
