import { describe, expect, it } from 'vitest';
import { describePlay, LivePlan } from '#features/tasks/livePlan.svelte.ts';
import { parameters, plan } from './fixtures.ts';

function setup() {
	const live = new LivePlan();
	live.session.useDefaults(parameters());
	return live;
}

const square = [
	{ x: 0, y: 0 },
	{ x: 2, y: 0 },
	{ x: 2, y: 2 }
];

describe('LivePlan', () => {
	it('asks for the whole garden by default', () => {
		const live = setup();
		expect(live.request).toEqual({ parts: [{ selection: [], parameters: parameters() }] });
		live.start();
		expect(live.drawing).toBe(false);
	});

	it('waits for a drawn area and draws only while open', () => {
		const live = setup();
		live.session.setTool('polygon');
		expect(live.request).toBeNull();
		expect(live.drawing).toBe(false);
		live.start();
		expect(live.drawing).toBe(true);
		square.forEach((p) => live.interact.tap!(p, 0.01));
		expect(live.request?.parts?.[0].selection).toEqual(square);
		live.close();
		expect(live.drawing).toBe(false);
	});

	it('asks for the chosen tasks in order', () => {
		const live = setup();
		live.mode = 'tasks';
		expect(live.request).toBeNull();
		live.session.toggle('t2');
		live.session.toggle('t1');
		expect(live.request).toEqual({ taskIds: ['t2', 't1'] });
	});

	it('knows whether a plan was calculated for the current choice', () => {
		const live = setup();
		const p = plan();
		expect(live.matches(p)).toBe(true);
		live.session.part!.parameters.borderLaps = 3;
		expect(live.matches(p)).toBe(false);
		live.mode = 'tasks';
		live.session.toggle('t1');
		expect(live.matches(plan({ taskIds: ['t1'] }))).toBe(true);
	});

	it('takes over the plan of saved tasks once', () => {
		const live = setup();
		live.adopt(plan({ taskIds: ['t1', 't2'] }));
		expect(live.mode).toBe('tasks');
		expect(live.session.chosen).toEqual(['t1', 't2']);
		live.adopt(plan());
		expect(live.mode).toBe('tasks');
	});

	it('keeps a plan with several parts until started over', () => {
		const live = setup();
		const part = { selection: square, parameters: parameters() };
		const p = plan({ parts: [part, part] });
		live.adopt(p);
		live.start();
		expect(live.editable).toBe(false);
		expect(live.drawing).toBe(false);
		expect(live.matches(p)).toBe(true);
		live.startOver();
		expect(live.editable).toBe(true);
		expect(live.session.tool).toBe('all');
	});
});

describe('play', () => {
	const garden = {
		kind: 'garden',
		request: { parts: [{ selection: [], parameters: parameters() }] }
	};

	it('waits for the mow settings', () => {
		expect(new LivePlan().play(false)).toBeNull();
	});

	it('mows the whole garden with the mow settings when nothing is chosen', () => {
		const live = setup();
		live.session.part!.parameters.pattern = 'rings';
		expect(live.play(false)).toEqual({
			kind: 'garden',
			request: { parts: [{ selection: [], parameters: parameters({ pattern: 'rings' }) }] }
		});
		expect(describePlay(live.play(false))).toBe('Mow: the whole garden');
	});

	it('goes on with an interrupted route when nothing is chosen', () => {
		const live = setup();
		expect(live.play(true)).toEqual({ kind: 'resume' });
		live.start(); // whole garden in the open planner is no choice either
		expect(live.play(true)).toEqual({ kind: 'resume' });
		expect(describePlay(live.play(true))).toBe('Mow: the route on the robot');
	});

	it('mows the route on the robot without an active map', () => {
		expect(setup().play(false, false)).toEqual({ kind: 'resume' });
	});

	it('mows only the drawn area', () => {
		const live = setup();
		live.start();
		live.session.setTool('polygon');
		expect(live.play(true)).toEqual({ kind: 'resume' }); // not drawn yet
		square.forEach((p) => live.session.tap(p));
		const action = live.play(true);
		expect(action).toMatchObject({ kind: 'area' });
		expect(action?.kind !== 'resume' && action?.request.parts?.[0].selection).toEqual(square);
		expect(describePlay(action)).toBe('Mow: the drawn area');
	});

	it('mows the chosen tasks in order', () => {
		const live = setup();
		live.start();
		live.mode = 'tasks';
		live.session.toggle('t2');
		live.session.toggle('t1');
		expect(live.play(true)).toEqual({ kind: 'tasks', request: { taskIds: ['t2', 't1'] } });
		expect(describePlay(live.play(true))).toBe('Mow: the 2 chosen tasks');
	});

	it('ignores a choice in the closed planner', () => {
		const live = setup();
		live.mode = 'tasks';
		live.session.toggle('t1');
		expect(live.play(false)).toEqual(garden);
	});

	it('mows a route of several parts from the Tasks page as chosen', () => {
		const live = setup();
		const part = { selection: square, parameters: parameters() };
		live.adopt(plan({ parts: [part, part] }));
		live.start();
		expect(live.play(true)).toEqual({ kind: 'area', request: { parts: [part, part] } });
	});
});
