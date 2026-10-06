// "Explore the tower": a night render of Meridian Heights (fictional) in the same look as the film — cream balcony
// bands, blue glass, gold-lit crown, a palm island in a marina with a lit skyline — where every flat's room light
// carries its CoolScore grade. Real time, eased camera moves, a reveal scan, drag with inertia.
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { Water } from 'three/addons/objects/Water.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const D2R = Math.PI / 180;
const N = 24;                 // residential floors
const FH = 3.4;               // floor to floor (m)
const ST = 0.34;              // slab thickness
const R = 13.6;               // glass line (octagon circumradius)
const RS = 15.6;              // balcony slab edge
const PH = 8.6;               // podium height
const Y0 = PH + 0.7;          // top of floor 1's slab
export const floorTop = (n) => Y0 + (n - 1) * FH;
const ROOF = floorTop(N + 1);
const CROWN = 4.4;
const COS8 = Math.cos(Math.PI / 8), SIN8 = Math.sin(Math.PI / 8);
const FACINGS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
// grade light colours (linear, bright enough to bloom)
const GRADE_LIGHT = ['#33e08a', '#9be35a', '#ffc94d', '#ff8a3d', '#ff4a4a'];

const rng = (seed) => () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const dir = (az) => [Math.sin(az * D2R), -Math.cos(az * D2R)];          // compass → (x, z); north = −z
function octPts(r, start = 22.5) { return Array.from({ length: 8 }, (_, k) => { const a = (start + 45 * k) * D2R; return new THREE.Vector2(Math.sin(a) * r, Math.cos(a) * r); }); }
function octShape(r, hole = 0) {
  const s = new THREE.Shape(octPts(r));
  if (hole) s.holes.push(new THREE.Path(octPts(hole).reverse()));
  return s;
}
function extrude(shape, depth, y, bevel = 0) {
  const g = new THREE.ExtrudeGeometry(shape, bevel ? { depth: depth - 2 * bevel, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 3, curveSegments: 4 } : { depth, bevelEnabled: false });
  g.rotateX(-Math.PI / 2); g.translate(0, y + bevel, 0);
  return g;
}
function canvasTex(w, h, draw, srgb = true) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  return t;
}
// quads around an octagon band (8 facets), with per-facet attributes
function octBand(r, y0, y1, extra = (k) => ({})) {
  const pos = [], nor = [], uv = [], idx = [], attrs = {};
  for (let k = 0; k < 8; k++) {
    const a0 = (k * 45 - 22.5) * D2R, a1 = (k * 45 + 22.5) * D2R;
    const p0 = [Math.sin(a0) * r, -Math.cos(a0) * r], p1 = [Math.sin(a1) * r, -Math.cos(a1) * r];
    const n = dir(k * 45), b = pos.length / 3;
    for (const [p, y, u, v] of [[p0, y0, 0, 0], [p1, y0, 1, 0], [p1, y1, 1, 1], [p0, y1, 0, 1]]) { pos.push(p[0], y, p[1]); nor.push(n[0], 0, n[1]); uv.push(u, v); }
    const ex = extra(k);
    for (const [name, val] of Object.entries(ex)) { (attrs[name] ||= []).push(val, val, val, val); }
    idx.push(b, b + 2, b + 1, b, b + 3, b + 2);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  for (const [name, arr] of Object.entries(attrs)) g.setAttribute(name, new THREE.Float32BufferAttribute(arr, 1));
  g.setIndex(idx);
  return g;
}

// ---------------- shaders ----------------
const SKY = /* glsl */`
uniform vec3 uZenith; uniform vec3 uHorizon; uniform vec3 uGlow; uniform vec3 uWarm;
vec3 skyCol(vec3 d) {
  float h = d.y;
  vec3 c = mix(uHorizon, uZenith, pow(clamp(h, 0.0, 1.0), 0.55));
  c += uGlow * exp(-max(h, 0.0) * 9.0) * 0.55;
  c += uWarm * exp(-max(h, 0.0) * 26.0) * 0.35;
  c = mix(c, uHorizon * 0.28, 1.0 - smoothstep(-0.06, 0.0, h));
  return c;
}`;
const GLASS_VERT = /* glsl */`
attribute float aFloor; attribute float aFacet; attribute float aGrade; attribute float aRand;
varying vec3 vW; varying vec3 vN; varying vec2 vUv; varying float vFloor; varying float vFacet; varying float vGrade; varying float vRand;
#include <fog_pars_vertex>
void main() {
  vec4 wp = modelMatrix * vec4(position, 1.0); vW = wp.xyz; vN = normalize(mat3(modelMatrix) * normal); vUv = uv;
  vFloor = aFloor; vFacet = aFacet; vGrade = aGrade; vRand = aRand;
  vec4 mvPosition = viewMatrix * wp; gl_Position = projectionMatrix * mvPosition;
  #include <fog_vertex>
}`;
const GLASS_FRAG = /* glsl */`
${SKY}
uniform float uData; uniform float uReveal; uniform float uSelFloor; uniform float uSelFacet; uniform float uHasSel;
uniform float uHoverFloor; uniform float uHoverFacet; uniform float uTime;
uniform vec3 uGrades[5];
varying vec3 vW; varying vec3 vN; varying vec2 vUv; varying float vFloor; varying float vFacet; varying float vGrade; varying float vRand;
#include <fog_pars_fragment>
float h21(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float is(float a, float b) { return 1.0 - step(0.5, abs(a - b)); }
void main() {
  vec3 Nn = normalize(vN), V = normalize(cameraPosition - vW);
  float ndv = clamp(dot(Nn, V), 0.0, 1.0);
  float F = 0.04 + 0.96 * pow(1.0 - ndv, 5.0);
  vec3 sky = skyCol(reflect(-V, Nn));

  // six bays per flat, with mullions and a sill
  float bx = clamp(vUv.x, 0.0, 0.9999) * 6.0, bay = floor(bx), fx = fract(bx);
  float frame = smoothstep(0.0, 0.035, fx) * (1.0 - smoothstep(0.965, 1.0, fx)) * smoothstep(0.0, 0.05, vUv.y) * (1.0 - smoothstep(0.93, 1.0, vUv.y));
  float r1 = h21(vec2(vFloor * 13.1 + vFacet, bay)), r2 = h21(vec2(bay * 3.7 + vFacet, vFloor * 1.31));
  float curtain = step(0.6, r2) * smoothstep(0.15, 0.25, abs(fx - 0.5));
  float ceil = 0.3 + 0.95 * smoothstep(0.05, 1.0, vUv.y);

  // the film's look: a few warm rooms on
  vec3 warm = mix(vec3(1.0, 0.66, 0.36), vec3(1.0, 0.84, 0.6), r2);
  vec3 real = warm * step(r1, 0.2) * ceil * (1.0 - 0.6 * curtain) * 1.25;

  // data view: every room lit in its grade colour, revealed by a scan rising floor by floor
  int gi = int(clamp(vGrade + 0.5, 0.0, 4.0));
  vec3 g = uGrades[gi];
  float front = uReveal * 25.0;
  float shown = 1.0 - smoothstep(front - 1.2, front - 0.2, vFloor);
  float d = vFloor - front; float edge = exp(-d * d * 1.6) * step(0.001, uReveal) * step(uReveal, 0.999);
  float sel = uHasSel * is(vFloor, uSelFloor), selU = sel * is(vFacet, uSelFacet);
  float hov = is(vFloor, uHoverFloor) * is(vFacet, uHoverFacet);
  float lvl = mix(1.0, mix(0.42, 1.25, sel), uHasSel);
  float k = (0.62 + 0.38 * r1) * ceil * (1.0 - 0.45 * curtain) * lvl;
  vec3 data = g * k * (1.0 + selU * (0.9 + 0.45 * sin(uTime * 3.2)) + hov * 0.9) * 1.15;
  vec3 room = mix(real, data, uData * shown) + g * edge * uData * 2.4;

  vec3 col = vec3(0.01, 0.018, 0.032) + room;
  float refl = clamp(F * 0.85 + 0.16, 0.0, 1.0) * (1.0 - clamp(dot(room, vec3(0.33)) * 0.7, 0.0, 0.75));
  col = mix(col, sky, refl);
  col = mix(vec3(0.05, 0.055, 0.065) + sky * 0.08, col, frame);
  gl_FragColor = vec4(max(col, 0.0), 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
  #include <fog_fragment>
}`;
// LED strip under each balcony edge, one segment per flat
const STRIP_FRAG = /* glsl */`
uniform float uData; uniform float uReveal; uniform float uSelFloor; uniform float uSelFacet; uniform float uHasSel; uniform float uTime;
uniform vec3 uGrades[5];
varying vec3 vW; varying vec3 vN; varying vec2 vUv; varying float vFloor; varying float vFacet; varying float vGrade; varying float vRand;
#include <fog_pars_fragment>
float is(float a, float b) { return 1.0 - step(0.5, abs(a - b)); }
void main() {
  int gi = int(clamp(vGrade + 0.5, 0.0, 4.0));
  float shown = 1.0 - smoothstep(uReveal * 25.0 - 1.2, uReveal * 25.0 - 0.2, vFloor);
  float sel = uHasSel * is(vFloor, uSelFloor), selU = sel * is(vFacet, uSelFacet);
  float lvl = mix(1.0, mix(0.35, 1.6, sel), uHasSel);
  float ends = smoothstep(0.0, 0.04, vUv.x) * (1.0 - smoothstep(0.96, 1.0, vUv.x));
  vec3 c = mix(vec3(1.0, 0.8, 0.55) * 0.35, uGrades[gi] * 1.6 * lvl * (1.0 + selU * 0.8), uData * shown) * ends;
  gl_FragColor = vec4(c, 1.0);
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
  #include <fog_fragment>
}`;
const FINISH = {
  uniforms: { tDiffuse: { value: null }, uTime: { value: 0 }, uRes: { value: new THREE.Vector2(1, 1) } },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
  fragmentShader: /* glsl */`
    uniform sampler2D tDiffuse; uniform float uTime; uniform vec2 uRes; varying vec2 vUv;
    void main() {
      vec2 q = vUv - 0.5;
      float ca = dot(q, q) * 0.0035;
      vec3 c = vec3(texture2D(tDiffuse, vUv + q * ca).r, texture2D(tDiffuse, vUv).g, texture2D(tDiffuse, vUv - q * ca).b);
      c *= clamp(1.0 - dot(q, q) * 0.9, 0.0, 1.0);
      float g = fract(sin(dot(vUv * uRes + fract(uTime) * 71.3, vec2(12.9898, 78.233))) * 43758.5453);
      c += (g - 0.5) * 0.018 * (0.2 + min(c, vec3(1.0)));
      gl_FragColor = vec4(max(c, 0.0), 1.0);
    }`,
};

export class TowerView {
  constructor(canvas, { mobile = false } = {}) {
    this.canvas = canvas;
    this.mobile = mobile;
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance' });
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.scene = new THREE.Scene();
    this.scene.fog = new THREE.FogExp2(0x12275a, 0.00085);
    this.camera = new THREE.PerspectiveCamera(32, 1, 1, 9000);
    this.tier = mobile ? 1 : 2;
    this.time = 0;
    this.fps = { n: 0, t: 0, low: 0 };
    this.U = {
      uZenith: { value: new THREE.Color('#071640') }, uHorizon: { value: new THREE.Color('#2a4fa6') },
      uGlow: { value: new THREE.Color('#5a4aa8') }, uWarm: { value: new THREE.Color('#ff9a5c') },
      uData: { value: 0 }, uReveal: { value: 0 }, uSelFloor: { value: -10 }, uSelFacet: { value: -10 }, uHasSel: { value: 0 },
      uHoverFloor: { value: -10 }, uHoverFacet: { value: -10 }, uTime: { value: 0 },
      uGrades: { value: GRADE_LIGHT.map((h) => new THREE.Color(h)) },
    };
    // camera state, eased toward goals
    this.cam = { az: 205, r: 300, ty: 50, up: 70, azGoal: 205, rGoal: 190, tyGoal: 50, upGoal: 8, vel: 0, dragging: false, idle: 0 };
    this.intro = 0; this.introOn = false;   // seconds since the section first came into view
    this.dataGoal = 1;
    this.build();
    this.setupPost();
    this.resize();
  }

  // ---------- scene ----------
  build() {
    const s = this.scene, U = this.U;
    // sky dome
    const sky = new THREE.Mesh(new THREE.SphereGeometry(5000, 48, 24), new THREE.ShaderMaterial({
      uniforms: { ...U }, side: THREE.BackSide, depthWrite: false, fog: false,
      vertexShader: 'varying vec3 vD; void main(){ vD = position; vec4 p = projectionMatrix * modelViewMatrix * vec4(position, 1.0); gl_Position = p.xyww; }',
      fragmentShader: `${SKY}
        varying vec3 vD;
        float h31(vec3 p) { p = fract(p * 0.1031); p += dot(p, p.zyx + 31.32); return fract((p.x + p.y) * p.z); }
        void main() {
          vec3 d = normalize(vD); vec3 c = skyCol(d);
          vec3 p = d * 300.0; float hs = h31(floor(p));
          c += vec3(0.85, 0.9, 1.0) * step(0.9975, hs) * (1.0 - smoothstep(0.0, 0.45, length(fract(p) - 0.5))) * smoothstep(0.08, 0.4, d.y) * 0.9;
          gl_FragColor = vec4(max(c, 0.0), 1.0);
          #include <tonemapping_fragment>
          #include <colorspace_fragment>
        }`,
    }));
    sky.frustumCulled = false; sky.renderOrder = -10;
    s.add(sky);
    this.sky = sky;

    // environment for reflections: the same sky plus the glow of the city on the horizon
    const env = new THREE.Scene();
    env.add(new THREE.Mesh(new THREE.SphereGeometry(100, 32, 16), sky.material));
    const glow = new THREE.Mesh(new THREE.CylinderGeometry(90, 90, 10, 48, 1, true), new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffb070').multiplyScalar(0.55), side: THREE.BackSide }));
    glow.position.y = 3; env.add(glow);
    const pm = new THREE.PMREMGenerator(this.renderer);
    s.environment = pm.fromScene(env, 0.03, 0.1, 300).texture;
    s.environmentIntensity = 0.9;

    // light: a cool sky fill and a warm uplight wash from the island
    s.add(new THREE.HemisphereLight(0x6f8fd8, 0x1a1410, 0.55));
    const moon = new THREE.DirectionalLight(0x9db6ff, 0.55); moon.position.set(-300, 500, 200); s.add(moon);
    const up = new THREE.SpotLight(0xffc98a, 2400, 140, 0.55, 0.8, 2); up.position.set(0, 2, 34); up.target.position.set(0, 60, 0); s.add(up, up.target);
    const up2 = up.clone(); up2.position.set(-30, 2, -18); up2.target.position.set(0, 55, 0); s.add(up2, up2.target);

    this.buildTower();
    this.buildIsland();
    this.buildCity();
    this.buildWater();
  }

  buildTower() {
    const s = this.scene, U = this.U;
    const cream = new THREE.MeshStandardMaterial({ color: '#ece6db', roughness: 0.42, metalness: 0.0, envMapIntensity: 1.1 });
    this.cream = cream;
    // balcony slabs with soft rounded edges
    const slabs = [];
    for (let n = 1; n <= N + 1; n++) slabs.push(extrude(octShape(RS), ST, floorTop(n) - ST, 0.08));
    slabs.push(extrude(octShape(RS + 0.4), 1.0, Y0 - 1.0, 0.1));                 // transfer slab
    slabs.push(extrude(octShape(R - 0.2), ROOF - Y0, Y0));                        // core behind the glass
    const slabMesh = new THREE.Mesh(mergeGeometries(slabs), cream);
    s.add(slabMesh);

    // glass: one panel per flat per floor
    const geos = [];
    const r = rng(17);
    for (let n = 1; n <= N; n++) {
      const g = octBand(R, floorTop(n), floorTop(n + 1) - ST, (k) => ({ aFloor: n, aFacet: k, aGrade: 2, aRand: r() }));
      geos.push(g);
    }
    const glassGeo = mergeGeometries(geos);
    this.glassMat = new THREE.ShaderMaterial({ uniforms: { ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog), ...U }, vertexShader: GLASS_VERT, fragmentShader: GLASS_FRAG, fog: true });
    this.glass = new THREE.Mesh(glassGeo, this.glassMat);
    s.add(this.glass);

    // balcony glass balustrades
    const rails = [];
    for (let n = 1; n <= N; n++) rails.push(octBand(RS - 0.12, floorTop(n), floorTop(n) + 1.05));
    const railMat = new THREE.MeshStandardMaterial({ color: '#a9c8ee', metalness: 0.9, roughness: 0.06, transparent: true, opacity: 0.22, envMapIntensity: 1.6, side: THREE.DoubleSide, depthWrite: false });
    const railMesh = new THREE.Mesh(mergeGeometries(rails), railMat); railMesh.renderOrder = 2; s.add(railMesh);
    const capRails = [];
    for (let n = 1; n <= N; n++) capRails.push(octBand(RS - 0.1, floorTop(n) + 1.03, floorTop(n) + 1.09));
    s.add(new THREE.Mesh(mergeGeometries(capRails), new THREE.MeshStandardMaterial({ color: '#d9dde3', metalness: 0.8, roughness: 0.3, side: THREE.DoubleSide })));

    // LED strip under each balcony edge (one segment per flat)
    const strips = [];
    for (let n = 1; n <= N; n++) {
      const y = floorTop(n + 1) - ST - 0.03;
      strips.push(octBand(RS - 0.35, y - 0.07, y, (k) => ({ aFloor: n, aFacet: k, aGrade: 2, aRand: 0 })));
    }
    this.stripMat = new THREE.ShaderMaterial({ uniforms: { ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog), ...U }, vertexShader: GLASS_VERT, fragmentShader: STRIP_FRAG, fog: true, side: THREE.DoubleSide });
    this.strips = new THREE.Mesh(mergeGeometries(strips), this.stripMat);
    s.add(this.strips);

    // vertical fins: a pair at each facade centre, a column at each corner
    const H = ROOF + CROWN - PH;
    const fin = new THREE.BoxGeometry(0.2, H, 0.9);
    const fins = new THREE.InstancedMesh(fin, cream, 8 * 3);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), one = new THREE.Vector3(1, 1, 1);
    let i = 0;
    for (let k = 0; k < 8; k++) {
      const [nx, nz] = dir(k * 45), tx = -nz, tz = nx, d = R * COS8 + 0.55;
      q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), -k * 45 * D2R);
      for (const u of [-0.42, 0.42]) { m.compose(new THREE.Vector3(nx * d + tx * u, PH + H / 2, nz * d + tz * u), q, one); fins.setMatrixAt(i++, m); }
      const a = (k * 45 + 22.5) * D2R, rr = (R + RS) / 2;
      m.compose(new THREE.Vector3(Math.sin(a) * rr, PH + H / 2, -Math.cos(a) * rr), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -(k * 45 + 22.5) * D2R), new THREE.Vector3(2.4, 1, 1.4));
      fins.setMatrixAt(i++, m);
    }
    s.add(fins);

    // crown: an open frame with a gold LED outline, like the film
    const crown = [];
    crown.push(extrude(octShape(RS + 0.1, RS - 1.1), 0.7, ROOF + CROWN - 0.7, 0.06));
    for (let k = 0; k < 8; k++) {
      const a = (k * 45 + 22.5) * D2R, rr = RS - 0.5;
      const b = new THREE.BoxGeometry(0.7, CROWN, 0.7); b.translate(Math.sin(a) * rr, ROOF + CROWN / 2, -Math.cos(a) * rr); crown.push(b.toNonIndexed());
    }
    s.add(new THREE.Mesh(mergeGeometries(crown.map((g) => g.index ? g.toNonIndexed() : g)), cream));
    const gold = new THREE.MeshBasicMaterial({ color: new THREE.Color('#ffb347').multiplyScalar(5), fog: true });
    const led = [octBand(RS + 0.14, ROOF + CROWN - 0.12, ROOF + CROWN - 0.02), octBand(RS + 0.14, ROOF + CROWN - 0.68, ROOF + CROWN - 0.6)];
    for (let k = 0; k < 8; k++) {
      const a = (k * 45 + 22.5) * D2R, rr = RS - 0.12;
      const b = new THREE.BoxGeometry(0.08, CROWN - 0.7, 0.08); b.translate(Math.sin(a) * rr, ROOF + (CROWN - 0.7) / 2, -Math.cos(a) * rr); led.push(b);
    }
    s.add(new THREE.Mesh(mergeGeometries(led.map((g) => (g.index ? g.toNonIndexed() : g))), gold));
    const plant = new THREE.Mesh(new THREE.BoxGeometry(9, 3, 7), new THREE.MeshStandardMaterial({ color: '#c9c4bb', roughness: 0.8 })); plant.position.set(0, ROOF + 1.5, 0); s.add(plant);

    // selected-floor halo: a gold band that glides to the chosen floor
    this.halo = new THREE.Mesh(octBand(RS + 0.18, -0.09, 0.09), new THREE.ShaderMaterial({
      uniforms: { uTime: U.uTime, uA: { value: 0 } }, transparent: true, depthWrite: false, side: THREE.DoubleSide,
      vertexShader: 'varying vec2 vUv; varying vec3 vP; void main(){ vUv = uv; vP = position; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
      fragmentShader: `uniform float uTime; uniform float uA; varying vec3 vP;
        void main(){ float a = atan(vP.z, vP.x); float sweep = 0.55 + 0.45 * sin(a * 2.0 - uTime * 2.4);
          gl_FragColor = vec4(vec3(1.0, 0.72, 0.28) * (2.2 + 2.6 * sweep), uA); }`,
    }));
    this.halo.position.y = floorTop(14) - ST / 2;
    s.add(this.halo);
  }

  buildIsland() {
    const s = this.scene;
    // podium: a white slatted screen with warm light behind it
    const W = 40, D = 36;
    const inner = new THREE.Mesh(new THREE.BoxGeometry(W - 1.6, PH - 0.6, D - 1.6), new THREE.MeshStandardMaterial({ color: '#2a2018', emissive: '#ffb470', emissiveIntensity: 0.55, roughness: 0.6 }));
    inner.position.y = (PH - 0.6) / 2 + 1.2; s.add(inner);
    const cap = new THREE.Mesh(extrude(new THREE.Shape([new THREE.Vector2(-W / 2 - 0.6, -D / 2 - 0.6), new THREE.Vector2(W / 2 + 0.6, -D / 2 - 0.6), new THREE.Vector2(W / 2 + 0.6, D / 2 + 0.6), new THREE.Vector2(-W / 2 - 0.6, D / 2 + 0.6)]), 0.8, PH + 0.6 - 0.8, 0.1), this.cream);
    s.add(cap);
    const per = [[W, 0, D / 2, 0], [W, 0, -D / 2, 0], [D, W / 2, 0, 1], [D, -W / 2, 0, 1]];
    let count = 0; for (const [len] of per) count += Math.floor(len / 0.9);
    const slats = new THREE.InstancedMesh(new THREE.BoxGeometry(0.22, PH - 0.6, 0.5), this.cream, count);
    const m = new THREE.Matrix4(); let i = 0;
    for (const [len, x, z, side] of per) for (let j = 0; j < Math.floor(len / 0.9); j++) {
      const u = -len / 2 + 0.45 + j * 0.9;
      m.makeRotationY(side ? Math.PI / 2 : 0).setPosition(side ? x : u, (PH - 0.6) / 2 + 1.2, side ? u : z);
      slats.setMatrixAt(i++, m);
    }
    s.add(slats);

    // the island: a rounded quay with a stone edge, lawns, a promenade and palms
    const shape = new THREE.Shape();
    const ix = 46, iz = 40, rr = 18;
    shape.moveTo(-ix + rr, -iz); shape.lineTo(ix - rr, -iz); shape.quadraticCurveTo(ix, -iz, ix, -iz + rr); shape.lineTo(ix, iz - rr);
    shape.quadraticCurveTo(ix, iz, ix - rr, iz); shape.lineTo(-ix + rr, iz); shape.quadraticCurveTo(-ix, iz, -ix, iz - rr); shape.lineTo(-ix, -iz + rr); shape.quadraticCurveTo(-ix, -iz, -ix + rr, -iz);
    const deckTex = canvasTex(1024, 1024, (g, S) => {
      g.fillStyle = '#b9b0a2'; g.fillRect(0, 0, S, S);
      const r = rng(5);
      for (let y = 0; y < S; y += 16) for (let x = (y / 16) % 2 ? 0 : 8; x < S; x += 32) { g.fillStyle = `hsl(36, 10%, ${58 + r() * 10}%)`; g.fillRect(x, y, 31, 15); }
      g.fillStyle = '#2e4a2c'; for (const [x, y, w, h] of [[60, 80, 300, 160], [650, 90, 300, 150], [70, 780, 280, 170], [680, 770, 270, 180]]) { g.beginPath(); g.roundRect(x, y, w, h, 40); g.fill(); }
      for (let k = 0; k < 900; k++) { g.fillStyle = `rgba(20,40,18,${r() * 0.4})`; g.beginPath(); g.arc(r() * S, r() * S, 2 + r() * 4, 0, 7); g.fill(); }
    });
    const top = new THREE.MeshStandardMaterial({ map: deckTex, roughness: 0.85 });
    const edge = new THREE.MeshStandardMaterial({ color: '#8b8172', roughness: 0.9 });
    const island = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: 2.4, bevelEnabled: true, bevelThickness: 0.2, bevelSize: 0.3, bevelSegments: 2, curveSegments: 16 }), [top, edge]);
    island.rotation.x = -Math.PI / 2; island.position.y = -1.6;
    // map the deck texture across the top
    const uv = island.geometry.attributes.uv, p = island.geometry.attributes.position;
    for (let k = 0; k < uv.count; k++) uv.setXY(k, (p.getX(k) + ix) / (2 * ix), (p.getY(k) + iz) / (2 * iz));
    s.add(island);
    const pool = new THREE.Mesh(new THREE.BoxGeometry(18, 0.1, 6), new THREE.MeshStandardMaterial({ color: '#0f6f86', emissive: '#1fb5d6', emissiveIntensity: 1.1, roughness: 0.1 }));
    pool.position.set(-6, 1.06, 29); s.add(pool);

    // promenade lights round the quay (they also reflect in the water)
    const lamps = [];
    const pts = shape.getSpacedPoints(70);
    for (const v of pts) lamps.push(v.x * 0.97, 2.6, -v.y * 0.97);
    for (let k = 0; k < 36; k++) { const a = (k / 36) * Math.PI * 2; lamps.push(Math.cos(a) * 18.9, PH + 1.3, Math.sin(a) * 17.1); }
    const lg = new THREE.BufferGeometry(); lg.setAttribute('position', new THREE.Float32BufferAttribute(lamps, 3));
    s.add(new THREE.Points(lg, new THREE.PointsMaterial({ color: new THREE.Color('#ffc27a').multiplyScalar(4), size: 1.6, map: this.dot(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })));
    const posts = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.06, 0.08, 2.4, 6), new THREE.MeshStandardMaterial({ color: '#2b2b2b', roughness: 0.6 }), pts.length);
    pts.forEach((v, k) => { m.makeTranslation(v.x * 0.97, 1.4, -v.y * 0.97); posts.setMatrixAt(k, m); });
    s.add(posts);
    this.buildPalms(shape);
  }

  buildPalms(shape) {
    const leaf = canvasTex(128, 512, (g, W, H) => {
      g.strokeStyle = '#fff'; g.lineCap = 'round'; g.lineWidth = 4; g.beginPath(); g.moveTo(W / 2, 0); g.lineTo(W / 2, H); g.stroke();
      for (let y = 10; y < H - 6; y += 9) { const t = y / H, len = (W / 2 - 4) * Math.sin(Math.PI * Math.min(1, t * 1.15)) ** 0.6; g.lineWidth = 3.2; g.beginPath(); g.moveTo(W / 2, y); g.lineTo(W / 2 - len, y + 22); g.moveTo(W / 2, y); g.lineTo(W / 2 + len, y + 22); g.stroke(); }
    });
    const fronds = [];
    for (let f = 0; f < 10; f++) {
      const phi = (f / 10) * Math.PI * 2, L = 3.6 - (f % 3) * 0.4, droop = 1.6 + (f % 4) * 0.25, seg = 10, pos = [], uv = [], idx = [];
      for (let i = 0; i <= seg; i++) {
        const t = i / seg, w = 0.6 * Math.sin(Math.PI * Math.min(1, t * 1.1)) ** 0.7 + 0.04;
        const x = Math.cos(phi) * L * t, z = Math.sin(phi) * L * t, y = 0.95 * L * t - droop * L * t * t * 0.55;
        pos.push(x + Math.sin(phi) * w, y, z - Math.cos(phi) * w, x - Math.sin(phi) * w, y, z + Math.cos(phi) * w); uv.push(0, t, 1, t);
        if (i < seg) { const b = i * 2; idx.push(b, b + 1, b + 2, b + 1, b + 3, b + 2); }
      }
      const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx); g.computeVertexNormals();
      fronds.push(g);
    }
    const spots = [];
    const r = rng(9);
    for (const v of shape.getSpacedPoints(26)) spots.push([v.x * 0.86, 0.8, -v.y * 0.86, 6 + r() * 3]);
    for (const [x, z] of [[17.6, 15.6], [-17.6, 15.6], [17.6, -15.6], [-17.6, -15.6], [18.4, 4], [-18.4, -4]]) spots.push([x, PH + 0.6, z, 4.5 + r() * 1.5]);   // podium corners, clear of the tower
    const trunkGeo = new THREE.CylinderGeometry(0.17, 0.27, 1, 7); trunkGeo.translate(0, 0.5, 0);
    const trunks = new THREE.InstancedMesh(trunkGeo, new THREE.MeshStandardMaterial({ color: '#6e5a45', roughness: 0.95 }), spots.length);
    const crowns = new THREE.InstancedMesh(mergeGeometries(fronds), new THREE.MeshStandardMaterial({ color: '#4f7340', map: leaf, alphaTest: 0.5, side: THREE.DoubleSide, roughness: 0.8, emissive: '#3a2a10', emissiveIntensity: 0.25 }), spots.length);
    const m = new THREE.Matrix4(), q = new THREE.Quaternion();
    const glows = [];
    spots.forEach(([x, y, z, h], i) => {
      q.setFromEuler(new THREE.Euler((r() - 0.5) * 0.12, r() * 6.28, (r() - 0.5) * 0.12));
      m.compose(new THREE.Vector3(x, y, z), q, new THREE.Vector3(1, h, 1)); trunks.setMatrixAt(i, m);
      const top = new THREE.Vector3(0, h, 0).applyQuaternion(q).add(new THREE.Vector3(x, y, z));
      m.compose(top, new THREE.Quaternion().setFromEuler(new THREE.Euler(0, r() * 6.28, 0)), new THREE.Vector3(1, 1, 1).multiplyScalar(0.9 + r() * 0.3)); crowns.setMatrixAt(i, m);
      glows.push(x, y + 0.4, z);
    });
    this.scene.add(trunks, crowns);
    const gg = new THREE.BufferGeometry(); gg.setAttribute('position', new THREE.Float32BufferAttribute(glows, 3));
    this.scene.add(new THREE.Points(gg, new THREE.PointsMaterial({ color: new THREE.Color('#ffb860').multiplyScalar(3), size: 3.2, map: this.dot(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })));
  }

  dot() {
    if (!this._dot) this._dot = canvasTex(64, 64, (g, W) => { const r = g.createRadialGradient(W / 2, W / 2, 0, W / 2, W / 2, W / 2); r.addColorStop(0, 'rgba(255,255,255,1)'); r.addColorStop(0.3, 'rgba(255,255,255,.5)'); r.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = r; g.fillRect(0, 0, W, W); }, false);
    return this._dot;
  }

  // facade textures for the city: dark glass with scattered lit windows
  facade(seed, lit, cool) {
    return canvasTex(256, 512, (g, W, H) => {
      const r = rng(seed);
      g.fillStyle = '#05080f'; g.fillRect(0, 0, W, H);
      const cols = 16, rows = 48, cw = W / cols, ch = H / rows;
      for (let y = 0; y < rows; y++) {
        const floorLit = r() < 0.85;                                   // some floors are dark
        for (let x = 0; x < cols; x++) {
          const on = floorLit && r() < lit;
          const warm = r() > cool;
          const l = on ? 28 + r() ** 2 * 45 : 2 + r() * 3;
          g.fillStyle = on ? (warm ? `hsl(${28 + r() * 14}, 80%, ${l}%)` : `hsl(${200 + r() * 25}, 45%, ${l}%)`) : `hsl(222, 30%, ${l}%)`;
          g.fillRect(x * cw + 1, y * ch + 2, cw - 2, ch - 3);
        }
      }
      g.fillStyle = 'rgba(120,130,150,.12)'; for (let y = 0; y < rows; y++) g.fillRect(0, y * ch, W, 1);
    });
  }

  buildCity() {
    const s = this.scene, r = rng(31);
    const texs = [this.facade(1, 0.26, 0.7), this.facade(2, 0.16, 0.5), this.facade(3, 0.32, 0.8), this.facade(4, 0.12, 0.35)];
    const groups = texs.map(() => []);
    const crowns = [];
    const add = (x, z, w, d, h, rot, v) => {
      const g = new THREE.BoxGeometry(w, h, d);
      const uv = g.attributes.uv, nm = g.attributes.normal;
      for (let i = 0; i < uv.count; i++) {
        const faceW = Math.abs(nm.getX(i)) > 0.5 ? d : w;
        if (Math.abs(nm.getY(i)) > 0.5) uv.setXY(i, 0.02, 0.02);              // roofs: a dark corner of the texture
        else uv.setXY(i, uv.getX(i) * faceW / 24, uv.getY(i) * h / 80);
      }
      g.rotateY(rot); g.translate(x, h / 2, z);
      groups[v].push(g.toNonIndexed());
    };
    // the marina's towers across the water, plus mid-rise along the quays
    for (let k = 0; k < 46; k++) {
      const a = (-40 + r() * 170) * D2R, dd = 300 + r() * 420;
      const h = 70 + r() ** 1.3 * 210, w = 24 + r() * 18;
      add(Math.sin(a) * dd, -Math.cos(a) * dd, w, w * (0.7 + r() * 0.5), h, r() * 0.8, k % 4);
      if (r() < 0.38) crowns.push([Math.sin(a) * dd, h, -Math.cos(a) * dd, w, ['#ff3fb4', '#3f8cff', '#ff3a3a', '#ffffff', '#7a5cff'][k % 5]]);
    }
    for (let k = 0; k < 70; k++) {
      const a = r() * Math.PI * 2, dd = 240 + r() * 300;
      add(Math.sin(a) * dd, -Math.cos(a) * dd, 20 + r() * 30, 18 + r() * 26, 10 + r() * 22, r() * 3, (k + 1) % 4);
    }
    for (let k = 0; k < 110; k++) {
      const a = r() * Math.PI * 2, dd = 900 + r() * 900;
      add(Math.sin(a) * dd, -Math.cos(a) * dd, 30 + r() * 40, 30 + r() * 40, 40 + r() ** 2 * 260, r() * 3, k % 4);
    }
    groups.forEach((gs, v) => {
      const t = texs[v]; t.wrapS = t.wrapT = THREE.RepeatWrapping;
      const mat = new THREE.MeshStandardMaterial({ color: '#10172a', roughness: 0.22, metalness: 0.6, emissive: '#ffffff', emissiveMap: t, emissiveIntensity: 1.6, envMapIntensity: 1.0 });
      s.add(new THREE.Mesh(mergeGeometries(gs), mat));
    });
    // coloured crown lights on some towers
    const cg = [];
    const colors = [];
    for (const [x, h, z, w, c] of crowns) {
      const b = new THREE.BoxGeometry(w + 0.6, 1.2, w * 0.8 + 0.6); b.translate(x, h + 0.2, z);
      const col = new THREE.Color(c).multiplyScalar(3);
      const nb = b.toNonIndexed(); const arr = []; for (let i = 0; i < nb.attributes.position.count; i++) arr.push(col.r, col.g, col.b);
      nb.setAttribute('color', new THREE.Float32BufferAttribute(arr, 3)); cg.push(nb);
    }
    s.add(new THREE.Mesh(mergeGeometries(cg), new THREE.MeshBasicMaterial({ vertexColors: true })));
    // the quay round the marina basin, with its lights
    const quay = new THREE.Mesh(new THREE.RingGeometry(185, 3200, 96, 1), new THREE.MeshStandardMaterial({ color: '#0c0f16', roughness: 0.9 }));
    quay.rotation.x = -Math.PI / 2; quay.position.y = 0.4; s.add(quay);
    const ql = [];
    for (let k = 0; k < 180; k++) { const a = (k / 180) * Math.PI * 2; ql.push(Math.cos(a) * 187, 3, Math.sin(a) * 187); }
    const qg = new THREE.BufferGeometry(); qg.setAttribute('position', new THREE.Float32BufferAttribute(ql, 3));
    s.add(new THREE.Points(qg, new THREE.PointsMaterial({ color: new THREE.Color('#ffb066').multiplyScalar(3.5), size: 2.4, map: this.dot(), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })));
  }

  buildWater() {
    // a tileable normal map drawn from summed waves (no texture download)
    const S = 256;
    const nrm = canvasTex(S, S, (g) => {
      const img = g.createImageData(S, S), r = rng(77), waves = Array.from({ length: 9 }, () => [Math.floor(1 + r() * 6) * (r() < 0.5 ? -1 : 1), Math.floor(1 + r() * 6), r() * 6.28, 0.4 + r()]);
      const hgt = (x, y) => waves.reduce((acc, [kx, ky, ph, a]) => acc + a * Math.sin((kx * x + ky * y) * 2 * Math.PI / S + ph), 0);
      for (let y = 0; y < S; y++) for (let x = 0; x < S; x++) {
        const dx = hgt(x + 1, y) - hgt(x - 1, y), dy = hgt(x, y + 1) - hgt(x, y - 1);
        const n = new THREE.Vector3(-dx * 0.9, -dy * 0.9, 1).normalize(), i = (y * S + x) * 4;
        img.data[i] = (n.x * 0.5 + 0.5) * 255; img.data[i + 1] = (n.y * 0.5 + 0.5) * 255; img.data[i + 2] = (n.z * 0.5 + 0.5) * 255; img.data[i + 3] = 255;
      }
      g.putImageData(img, 0, 0);
    }, false);
    nrm.wrapS = nrm.wrapT = THREE.RepeatWrapping;
    const size = this.tier >= 2 ? 1024 : 512;
    this.water = new Water(new THREE.PlaneGeometry(6000, 6000), {
      textureWidth: size, textureHeight: size, waterNormals: nrm, sunDirection: new THREE.Vector3(-0.4, 0.6, 0.5).normalize(),
      sunColor: 0x6a7fb8, waterColor: 0x04102a, distortionScale: 0.75, fog: true,
    });
    this.water.rotation.x = -Math.PI / 2;
    this.water.material.uniforms.size.value = 3.2;
    this.scene.add(this.water);
  }

  setupPost() {
    this.rt = new THREE.WebGLRenderTarget(4, 4, { type: THREE.HalfFloatType, samples: this.tier >= 2 ? 4 : 0 });
    this.composer = new EffectComposer(this.renderer, this.rt);
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.85, 0.62, 0.82);
    this.composer.addPass(this.bloom);
    this.finish = new ShaderPass(FINISH);
    this.composer.addPass(this.finish);
    this.composer.addPass(new OutputPass());
  }

  setTier(t) {
    if (t === this.tier) return;
    this.tier = t;
    for (const target of [this.composer.renderTarget1, this.composer.renderTarget2]) { target.samples = t >= 2 ? 4 : 0; target.dispose(); }
    this.resize();
  }

  resize() {
    const w = this.canvas.clientWidth || innerWidth, h = this.canvas.clientHeight || innerHeight;
    this.W = w; this.H = h;
    const dpr = Math.min(devicePixelRatio || 1, [1, 1.25, 1.75][this.tier]);
    this.renderer.setPixelRatio(dpr); this.renderer.setSize(w, h, false);
    this.composer.setPixelRatio(dpr); this.composer.setSize(w, h);
    this.finish.uniforms.uRes.value.set(w * dpr, h * dpr);
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
  }

  // ---------- data + interaction ----------
  setGrades(units) {
    const L = 'ABCDE', map = new Map(units.map((u) => [`${u.floor}:${FACINGS.indexOf(u.facing)}`, L.indexOf(u.score)]));
    for (const mesh of [this.glass, this.strips]) {
      const a = mesh.geometry.attributes, g = a.aGrade;
      for (let i = 0; i < g.count; i++) g.setX(i, map.get(`${a.aFloor.getX(i)}:${a.aFacet.getX(i)}`) ?? 2);
      g.needsUpdate = true;
    }
  }
  select(floor, facing, { turn = true } = {}) {
    this.sel = { floor, k: FACINGS.indexOf(facing) };
    this.cam.tyGoal = Math.min(64, Math.max(36, floorTop(floor) + 1.6)); this.cam.rGoal = 178; this.cam.upGoal = 4;
    if (turn) { let goal = this.sel.k * 45 + 18; const d = ((goal - this.cam.az) % 360 + 540) % 360 - 180; this.cam.azGoal = this.cam.az + d; this.cam.idle = -4; }
  }
  hover(h) { this.U.uHoverFloor.value = h ? h.floor : -10; this.U.uHoverFacet.value = h ? FACINGS.indexOf(h.facing) : -10; }
  setData(on) { this.dataGoal = on ? 1 : 0; }
  drag(dx) { this.cam.dragging = true; this.cam.az -= dx * 0.25; this.cam.azGoal = this.cam.az; this.cam.vel = -dx * 0.25 / Math.max(1 / 60, this.lastDt || 1 / 60); this.cam.idle = 0; }
  release() { this.cam.dragging = false; this.cam.idle = 0; }
  start() { this.introOn = true; }

  pick(nx, ny) {
    const rc = new THREE.Raycaster(); rc.setFromCamera(new THREE.Vector2(nx, ny), this.camera);
    const hit = rc.intersectObject(this.glass, false)[0];
    if (!hit) return null;
    const a = this.glass.geometry.attributes;
    return { floor: a.aFloor.getX(hit.face.a), facing: FACINGS[a.aFacet.getX(hit.face.a)] };
  }
  screenOf(floor, facing) {
    const [nx, nz] = dir(FACINGS.indexOf(facing) * 45), d = RS * COS8;
    const p = new THREE.Vector3(nx * d, floorTop(floor) + FH * 0.5, nz * d).project(this.camera);
    return { x: (p.x * 0.5 + 0.5) * this.W, y: (-p.y * 0.5 + 0.5) * this.H, z: p.z };
  }

  update(dt, { frame = 0 } = {}) {
    dt = Math.min(0.05, Math.max(0, dt || 0));
    this.lastDt = dt;
    this.time += dt; this.U.uTime.value = this.time;
    const c = this.cam, ease = (k) => 1 - Math.exp(-dt * k);
    // intro: a sweeping arrival, then the grade lights scan up the tower
    let introE = 1;
    if (this.introOn) {
      this.intro += dt;
      introE = 1 - (1 - Math.min(1, this.intro / 3.6)) ** 3;
      this.U.uReveal.value = Math.min(1, Math.max(0, (this.intro - 1.0) / 2.6));
    }
    this.U.uData.value += (this.dataGoal - this.U.uData.value) * ease(3);
    // camera: inertia when released, a slow drift when idle, eased moves to goals
    if (!c.dragging) {
      c.vel *= Math.exp(-dt * 2.8);
      c.idle += dt;
      if (Math.abs(c.vel) > 0.5) { c.az += c.vel * dt; c.azGoal = c.az; }
      else if (c.idle > 3) c.azGoal += dt * 3.2 * Math.min(1, (c.idle - 3) / 3);
      c.az += (c.azGoal - c.az) * ease(2.2);
    }
    c.r += (c.rGoal - c.r) * ease(2); c.ty += (c.tyGoal - c.ty) * ease(2); c.up += (c.upGoal - c.up) * ease(2);
    const az = (c.az - 70 * (1 - introE)) * D2R, rr = c.r + 160 * (1 - introE), upv = c.up + 70 * (1 - introE);
    this.camera.position.set(Math.sin(az) * rr, c.ty + upv, -Math.cos(az) * rr);
    this.camera.lookAt(0, c.ty, 0);
    const asp = this.W / this.H;
    this.camera.fov = asp < 1 ? Math.min(62, 2 * Math.atan(Math.tan(16 * D2R) * 1.2 / asp) / D2R) : 32;
    this.camera.setViewOffset(this.W, this.H, this.W * 0.16 * frame, 0, this.W, this.H);
    this.camera.updateProjectionMatrix();
    this.sky.position.copy(this.camera.position);
    // selection: halo glides to the floor, the rest of the tower dims a little
    if (this.sel) {
      this.U.uSelFloor.value = this.sel.floor; this.U.uSelFacet.value = this.sel.k;
      this.U.uHasSel.value += (1 - this.U.uHasSel.value) * ease(3);
      this.halo.position.y += (floorTop(this.sel.floor) - ST / 2 - this.halo.position.y) * ease(6);
      this.halo.material.uniforms.uA.value += (0.95 * this.U.uReveal.value - this.halo.material.uniforms.uA.value) * ease(4);
    }
    this.water.material.uniforms.time.value = this.time * 0.35;
    this.finish.uniforms.uTime.value = this.time;
    this.composer.render();
    this.trackFps(dt);
  }

  trackFps(dt) {
    const f = this.fps; f.n++; f.t += dt;
    if (this.time < 5) { f.n = 0; f.t = 0; return; }
    if (f.t > 2) { const fps = f.n / f.t; this.lastFps = fps; f.low = fps < 45 ? f.low + 1 : 0; if (f.low >= 2 && this.tier > 0) { this.setTier(this.tier - 1); f.low = 0; } f.n = 0; f.t = 0; }
  }
}
