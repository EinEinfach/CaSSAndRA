// Draws a garden map on a 2D canvas. Pure apart from the context it draws on.
import { toScreen, type Point, type Viewport } from './viewport.ts';

export interface RobotPose {
	position: Point;
	headingRad: number;
}

export interface MapLayers {
	perimeter?: Point[];
	exclusions?: Point[][];
	dock?: Point[];
	way?: Point[];
	/** Way points before this index are drawn as done. */
	wayDoneIndex?: number;
	trail?: Point[];
	target?: Point | null;
	robot?: RobotPose | null;
}

export interface MapColors {
	background: string;
	lawn: string;
	border: string;
	exclusion: string;
	dock: string;
	way: string;
	wayDone: string;
	trail: string;
	target: string;
	robot: string;
	robotOutline: string;
}

/** The subset of CanvasRenderingContext2D the map needs. */
export type MapContext = Pick<
	CanvasRenderingContext2D,
	| 'beginPath'
	| 'moveTo'
	| 'lineTo'
	| 'closePath'
	| 'arc'
	| 'fill'
	| 'stroke'
	| 'fillRect'
	| 'save'
	| 'restore'
	| 'translate'
	| 'rotate'
	| 'setLineDash'
> & {
	fillStyle: string | CanvasGradient | CanvasPattern;
	strokeStyle: string | CanvasGradient | CanvasPattern;
	lineWidth: number;
	lineJoin: CanvasLineJoin;
	lineCap: CanvasLineCap;
};

/** Robot drawn 0.6 m long, but never smaller than this many pixels. */
const ROBOT_LENGTH_M = 0.6;
const ROBOT_MIN_PX = 14;

export function drawMap(ctx: MapContext, vp: Viewport, layers: MapLayers, colors: MapColors): void {
	ctx.fillStyle = colors.background;
	ctx.fillRect(0, 0, vp.width, vp.height);
	ctx.lineJoin = 'round';
	ctx.lineCap = 'round';

	if (layers.perimeter?.length) {
		path(ctx, vp, layers.perimeter, true);
		ctx.fillStyle = colors.lawn;
		ctx.fill();
		ctx.strokeStyle = colors.border;
		ctx.lineWidth = 2;
		ctx.stroke();
	}
	for (const ex of layers.exclusions ?? []) {
		if (ex.length === 0) continue;
		path(ctx, vp, ex, true);
		ctx.fillStyle = colors.exclusion;
		ctx.fill();
	}

	const way = layers.way ?? [];
	const done = Math.max(0, Math.min(layers.wayDoneIndex ?? 0, way.length));
	if (done > 0) {
		path(ctx, vp, way.slice(0, done + 1), false);
		ctx.strokeStyle = colors.wayDone;
		ctx.lineWidth = 1;
		ctx.stroke();
	}
	if (way.length - done > 0) {
		path(ctx, vp, way.slice(Math.max(0, done - 1)), false);
		ctx.strokeStyle = colors.way;
		ctx.lineWidth = 1;
		ctx.stroke();
	}

	if (layers.dock?.length) {
		ctx.setLineDash([6, 4]);
		path(ctx, vp, layers.dock, false);
		ctx.strokeStyle = colors.dock;
		ctx.lineWidth = 2;
		ctx.stroke();
		ctx.setLineDash([]);
		dot(ctx, vp, layers.dock[layers.dock.length - 1], 5, colors.dock);
	}

	if (layers.trail && layers.trail.length > 1) {
		path(ctx, vp, layers.trail, false);
		ctx.strokeStyle = colors.trail;
		ctx.lineWidth = 3;
		ctx.stroke();
	}
	if (layers.target) {
		dot(ctx, vp, layers.target, 4, colors.target);
	}
	if (layers.robot) {
		drawRobot(ctx, vp, layers.robot, colors);
	}
}

function path(ctx: MapContext, vp: Viewport, pts: Point[], closed: boolean) {
	ctx.beginPath();
	pts.forEach((p, i) => {
		const s = toScreen(vp, p);
		if (i === 0) ctx.moveTo(s.x, s.y);
		else ctx.lineTo(s.x, s.y);
	});
	if (closed) ctx.closePath();
}

function dot(ctx: MapContext, vp: Viewport, p: Point, radius: number, color: string) {
	const s = toScreen(vp, p);
	ctx.beginPath();
	ctx.arc(s.x, s.y, radius, 0, 2 * Math.PI);
	ctx.fillStyle = color;
	ctx.fill();
}

/** An arrow pointing in the heading direction (0 = +x, counter-clockwise). */
function drawRobot(ctx: MapContext, vp: Viewport, robot: RobotPose, colors: MapColors) {
	const s = toScreen(vp, robot.position);
	const len = Math.max(ROBOT_LENGTH_M * vp.scale, ROBOT_MIN_PX);
	ctx.save();
	ctx.translate(s.x, s.y);
	ctx.rotate(-robot.headingRad); // screen y points down
	ctx.beginPath();
	ctx.moveTo(len / 2, 0);
	ctx.lineTo(-len / 2, len / 3);
	ctx.lineTo(-len / 4, 0);
	ctx.lineTo(-len / 2, -len / 3);
	ctx.closePath();
	ctx.fillStyle = colors.robot;
	ctx.fill();
	ctx.strokeStyle = colors.robotOutline;
	ctx.lineWidth = 2;
	ctx.stroke();
	ctx.restore();
}

/** Every point the map shows, for fitting the view. */
export function mapPoints(layers: MapLayers): Point[] {
	return [
		...(layers.perimeter ?? []),
		...(layers.exclusions ?? []).flat(),
		...(layers.dock ?? []),
		...(layers.way ?? []),
		...(layers.robot ? [layers.robot.position] : [])
	];
}
