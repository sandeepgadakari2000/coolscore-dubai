// The film's choreography. Scroll position s runs 0 → 11.5 (one unit = one screen of scroll):
//   0–1 intro (pre-dawn) · 1–3 sunrise · 3–5 afternoon · 5–7 evening · 7–9 night · 9–10.5 closing orbit
//   · 10.5–11.5 the 3D tower takes over for "explore". The filmed clips map onto the same ranges (film.js).
// Everything here is pure: clock, camera and sky palette are functions of s (and of the measured day).

export const TOWER = {
  floors: 24, floorH: 3.5, podiumH: 9, slab: 0.4,
  R: 15,            // glass line, octagon circumradius (m)
  Rslab: 15.75,     // slab edge
  coreR: 5.4,       // lift core
  fins: 3,          // vertical fins per facade
};
export const FACINGS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
export const FACING_WORDS = { N: 'North', NE: 'North-east', E: 'East', SE: 'South-east', S: 'South', SW: 'South-west', W: 'West', NW: 'North-west' };
export const COS8 = Math.cos(Math.PI / 8);
export const APOTHEM = TOWER.R * COS8;
export const floorY = (n) => TOWER.podiumH + (n - 1) * TOWER.floorH;      // top of floor n's slab
export const ROOF_Y = floorY(TOWER.floors + 1);
export const S_END = 11.5;

// compass azimuth (deg, clockwise from north) → world direction; north = −z, east = +x
export const dirOf = (azDeg, elDeg = 0) => {
  const a = azDeg * Math.PI / 180, e = elDeg * Math.PI / 180;
  return [Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e)];
};

// The four stops; floor/facing must match site/data/tower.json "featured".
export const CHAPTERS = [
  { key: 'intro', start: 0, end: 1 },
  { key: 'sunrise', start: 1, end: 3, floor: 17, facing: 'E', hour: 7 },
  { key: 'afternoon', start: 3, end: 5, floor: 24, facing: 'S', hour: 13 },
  { key: 'evening', start: 5, end: 7, floor: 14, facing: 'W', hour: 17 },
  { key: 'night', start: 7, end: 9, floor: 3, facing: 'N', hour: 22 },
  { key: 'closing', start: 9, end: 10.5 },
  { key: 'explore', start: 10.5, end: 11.5 },
];
export const chapterAt = (s) => { for (let i = CHAPTERS.length - 1; i > 0; i--) if (s >= CHAPTERS[i].start) return i; return 0; };

// ---------- monotone cubic interpolation (no overshoot, so holds stay holds) ----------
export function track(keys) {
  const xs = keys.map((k) => k[0]), ys = keys.map((k) => k[1]), n = xs.length;
  const d = [], m = new Array(n).fill(0);
  for (let i = 0; i < n - 1; i++) d.push((ys[i + 1] - ys[i]) / (xs[i + 1] - xs[i]));
  for (let i = 1; i < n - 1; i++) m[i] = d[i - 1] * d[i] <= 0 ? 0 : (d[i - 1] + d[i]) / 2;
  m[0] = d[0]; m[n - 1] = d[n - 2];
  for (let i = 0; i < n - 1; i++) {
    if (d[i] === 0) { m[i] = 0; m[i + 1] = 0; continue; }
    const a = m[i] / d[i], b = m[i + 1] / d[i], h = a * a + b * b;
    if (h > 9) { const t = 3 / Math.sqrt(h); m[i] = t * a * d[i]; m[i + 1] = t * b * d[i]; }
  }
  return (x) => {
    if (x <= xs[0]) return ys[0];
    if (x >= xs[n - 1]) return ys[n - 1];
    let i = 0; while (x > xs[i + 1]) i++;
    const h = xs[i + 1] - xs[i], t = (x - xs[i]) / h, t2 = t * t, t3 = t2 * t;
    return (2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1] + (t3 - t2) * h * m[i + 1];
  };
}

// ---------- clock (local hour) ----------
export const clockAt = track([
  [0, 5.5], [1.0, 6.1], [1.5, 6.75], [2.55, 7.35], [3.0, 9.6], [3.5, 12.7], [4.55, 13.3],
  [5.0, 15.1], [5.5, 16.6], [6.45, 17.4], [7.0, 18.95], [7.5, 21.4], [8.55, 22.2], [9.0, 22.5], [10.5, 22.8], [11.5, 22.9],
]);

// ---------- camera: cylindrical keys around the tower axis ----------
// th = camera azimuth (deg), r = distance, y = height; target at (tth, tr, ty); fov (deg, vertical at 16:9)
const CAM = [
  // s,    th,  r,   y,   tth, tr,  ty,  fov
  [0.0, 252, 245, 20, 0, 0, 50, 34],     // pre-dawn: the tower against the eastern glow
  [0.75, 214, 170, 30, 0, 0, 46, 32],
  [1.5, 128, 76, 72, 90, 4, 66, 30],
  [2.55, 110, 41, 68.6, 90, 7, 66.1, 30],  // floor 17, east, from just above its ceiling line, off the sun's axis
  [3.05, 122, 112, 80, 0, 0, 62, 32],
  [3.6, 160, 80, 128, 180, 4, 93, 32],
  [4.55, 170, 52, 113, 180, 8, 91, 34],   // the roof and the top floor
  [5.05, 216, 112, 80, 0, 0, 62, 32],
  [5.6, 244, 68, 62, 270, 4, 58, 30],
  [6.5, 254, 41, 58.1, 270, 7, 55.6, 30], // floor 14, west
  [7.05, 312, 132, 46, 0, 0, 50, 32],
  [7.6, 338, 66, 24, 360, 4, 20, 30],
  [8.55, 350, 41, 19.6, 360, 7, 17.1, 30], // floor 3, north, at night
  [9.1, 372, 150, 46, 360, 0, 50, 32],
  [10, 382, 198, 58, 360, 0, 52, 32],
];
const camTracks = Array.from({ length: 7 }, (_, j) => track(CAM.map((k) => [k[0], k[j + 1]])));
export function cameraAt(s) {
  if (s > 9) s = 9 + (s - 9) / 2.5;        // the 3D keys end at 10; closing + explore stretch over 9 → 11.5
  const [th, r, y, tth, tr, ty, fov] = camTracks.map((f) => f(s));
  return { th, r, y, tth, tr, ty, fov };
}

// ---------- the measured day: sun and weather at any clock time ----------
// Rows of climate_monthly are hourly means ending at the hour; sun geometry is at the half hour (t − 30 min).
const lerp = (a, b, t) => a + (b - a) * t;
function sample(arr, x) {
  const n = arr.length, i = Math.floor(x), t = x - i;
  return lerp(arr[((i % n) + n) % n], arr[(((i + 1) % n) + n) % n], t);
}
function sampleAngle(arr, x) {
  const n = arr.length, i = Math.floor(x), t = x - i;
  const a = arr[((i % n) + n) % n], b = arr[(((i + 1) % n) + n) % n];
  let d = ((b - a + 540) % 360) - 180;
  return (a + d * t + 360) % 360;
}
export function dayAt(clock, climate) {
  const h = climate.hourly;
  const x = clock + 0.5;          // row k describes [k−1, k), its sun geometry is at k − 0.5
  return {
    elev: sample(h.elev, x), az: sampleAngle(h.az, x),
    temp: sample(h.temp, clock), rh: sample(h.rh, clock),
    facade: (f) => Math.max(0, sample(h.facade[f], x)),
  };
}
export function loadAt(profile, clock) { return sample(profile, clock); }

// ---------- sky palette by sun elevation (deg) ----------
const hex = (h) => [parseInt(h.slice(1, 3), 16) / 255, parseInt(h.slice(3, 5), 16) / 255, parseInt(h.slice(5, 7), 16) / 255];
const PAL = [
  // elev, zenith,    horizon,   ground,    sun,       fog
  [-20, '#03050c', '#0a1022', '#05070d', '#9fb4ff', '#0a0f1e'],
  [-9, '#081130', '#1f2a52', '#0b0d16', '#9fb4ff', '#1a2142'],
  [-3, '#16285a', '#c9775f', '#1a1414', '#ff7a45', '#5a4458'],
  [1.5, '#2c4f8c', '#ffae74', '#3a2a22', '#ff8a4a', '#c88a6c'],
  [8, '#3f6eb0', '#f2bf8a', '#6b553f', '#ffb06a', '#d8b08c'],
  [22, '#4f86c8', '#e6d2b0', '#8c7a62', '#ffd39c', '#dccdb2'],
  [50, '#4c86cc', '#eadcc0', '#9a8870', '#fff0d8', '#e6d8bd'],
  [85, '#5590d2', '#f1e1c2', '#a08e75', '#fff4e2', '#ecdcbc'],
].map((r) => [r[0], ...r.slice(1).map(hex)]);
export function paletteAt(elev) {
  let i = 0; while (i < PAL.length - 2 && elev > PAL[i + 1][0]) i++;
  const a = PAL[i], b = PAL[i + 1];
  const t = Math.min(1, Math.max(0, (elev - a[0]) / (b[0] - a[0])));
  const s = t * t * (3 - 2 * t);
  const mix = (k) => a[k].map((v, j) => lerp(v, b[k][j], s));
  return { zenith: mix(1), horizon: mix(2), ground: mix(3), sun: mix(4), fog: mix(5) };
}

export const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
export const fmtClock = (c) => { const m = Math.round(((c % 24) + 24) % 24 * 60); return `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`; };
