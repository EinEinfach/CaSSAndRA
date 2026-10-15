import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import Nav, { type NavItem } from '#shared/Nav.svelte';

const items: NavItem[] = [
	{ href: '/', label: 'Live', icon: 'live' },
	{ href: '/maps', label: 'Maps', icon: 'maps' },
	{ href: '/settings', label: 'Settings', icon: 'settings' }
];

const current = () =>
	screen
		.getAllByRole('link')
		.filter((a) => a.getAttribute('aria-current') === 'page')
		.map((a) => a.textContent?.trim());

describe('Nav', () => {
	it('links all pages', () => {
		render(Nav, { items, current: '/' });
		expect(screen.getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual([
			'/',
			'/maps',
			'/settings'
		]);
	});

	it.each([
		['/', 'Live'],
		['/maps', 'Maps'],
		['/maps/abc', 'Maps'],
		['/settings', 'Settings']
	])('marks %s as %s', (path, label) => {
		render(Nav, { items, current: path });
		expect(current()).toEqual([label]);
	});

	it('does not mark a page that only shares a prefix', () => {
		render(Nav, { items, current: '/mapsmore' });
		expect(current()).toEqual([]);
	});

	it('shows version and connection', () => {
		render(Nav, { items, current: '/', version: 'v2.1', connected: false });
		expect(screen.getByText('v2.1')).toBeTruthy();
		expect(screen.getByTitle('No connection to CaSSAndRA')).toBeTruthy();
	});
});
