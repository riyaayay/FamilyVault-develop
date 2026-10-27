"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";
import Link from "next/link";
import { TILE_SRC } from "@/lib/landing/orb-tiles";
import { AVATARS } from "@/lib/landing/orb-avatars";

/* ----------------------------------------------------------------
   FamilyVault landing "sphere of memories" — ported from the
   orb.gallery authored source (Three.js r149) and remapped to our
   project. One plate per lattice cell on a rotating sphere; hover
   lift + focus dimming + grab/inertial drag.
   ---------------------------------------------------------------- */

const CSS = `
.orb-root{
  --bg:#ffffff; --ink:#17171a; --dim:rgba(23,23,26,.62);
  --faint:rgba(23,23,26,.45); --line:rgba(0,0,0,.10);
  --line-2:rgba(0,0,0,.18); --pad:clamp(20px,3.4vw,52px);
  position:relative; z-index:0; min-height:100dvh;
  color:var(--ink);
  overflow-x:hidden; overflow-y:visible;
  font-family:Geist,Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:16px; line-height:1.5; -webkit-font-smoothing:antialiased;
  background:var(--bg);
}
.orb-root *{box-sizing:border-box}
.orb-root a{color:inherit;text-decoration:none}

.orb__stage{ position:absolute; inset:0; z-index:0 }
.orb__stage.orb__stacked{ position:relative; inset:auto }
.orb__canvas{ position:absolute; inset:0; width:100%; height:100%; display:block;
  cursor:grab; touch-action:pan-y }
.orb__canvas.dragging{ cursor:grabbing }

.orb__nav{
  position:relative; z-index:3;
  display:flex; align-items:center; gap:clamp(20px,3vw,44px);
  padding:clamp(18px,2.3vw,28px) var(--pad);
}
.orb__logo{ display:flex; align-items:center; gap:10px; font-weight:600;
  letter-spacing:-.022em; font-size:17px; flex:0 0 auto }
.orb__logo svg{ width:23px; height:23px; flex:0 0 auto }
.orb__links{ display:flex; gap:clamp(16px,2vw,30px); margin-left:6px }
.orb__links a{ font-size:14.5px; color:var(--dim); transition:color .2s ease }
.orb__links a:hover{ color:var(--ink) }
.orb__navend{ margin-left:auto; display:flex; align-items:center; gap:clamp(12px,1.6vw,22px) }
.orb__navend .sign{ font-size:14.5px; color:var(--dim); transition:color .2s ease }
.orb__navend .sign:hover{ color:var(--ink) }

.orb__btn{ display:inline-flex; align-items:center; justify-content:center; gap:8px;
  border-radius:999px; font-weight:500; letter-spacing:-.012em; white-space:nowrap;
  transition:transform .3s cubic-bezier(.2,.7,.3,1), background .25s ease, border-color .25s ease }
.orb__btn:active{ transform:translateY(1px) }
.orb__btn.sm{ font-size:14px; padding:9px 17px }
.orb__btn.lg{ font-size:15.5px; padding:13px 25px }
.orb__btn.solid{ background:var(--ink); color:#fff }
.orb__btn.solid:hover{ background:#000 }
.orb__btn.ghost{ border:1px solid var(--line-2); color:var(--ink) }
.orb__btn.ghost:hover{ border-color:rgba(0,0,0,.38); background:rgba(0,0,0,.04) }
.orb__btn .orb__arrow{ transition:transform .3s cubic-bezier(.2,.7,.3,1) }
.orb__btn:hover .orb__arrow{ transform:translateX(3px) }

.orb__hint{
  position:relative; z-index:3; width:fit-content; margin:2px auto 0;
  display:flex; align-items:center; gap:9px;
  padding:8px 15px 8px 11px; border-radius:999px;
  background:rgba(0,0,0,.03); border:1px solid var(--line);
  font-size:12.5px; color:var(--faint); letter-spacing:-.004em;
  transition:opacity .5s ease, transform .5s ease; pointer-events:none;
}
.orb__hint svg{ width:14px; height:14px }
.orb__hint.gone{ opacity:0; transform:translateY(5px) }

.orb__band{
  position:absolute; left:0; right:0; bottom:0; z-index:3;
  display:grid; grid-template-columns:1fr 1fr; align-items:end;
  gap:clamp(24px,4vw,80px); padding:0 var(--pad) clamp(24px,4.4vh,52px);
}
.orb__lead{
  grid-column:1; justify-self:start; margin:0; font-weight:600;
  font-size:clamp(40px,5.2vw,72px); line-height:.98; letter-spacing:-.042em;
}
.orb__lead em{ font-family:Georgia,"Instrument Serif","Times New Roman",serif;
  font-style:italic; font-weight:400; letter-spacing:-.008em; margin-right:-.05em }
.orb__side{ grid-column:2; justify-self:end; max-width:min(100%,390px) }

.orb__badge{ display:inline-flex; align-items:center; gap:9px;
  padding:5px 13px 5px 10px; border-radius:999px;
  border:1px solid var(--line); background:rgba(0,0,0,.03);
  font-size:12.5px; color:var(--dim); letter-spacing:-.006em }
.orb__badge i{ width:6px; height:6px; border-radius:999px; background:#4ade80;
  box-shadow:0 0 0 3px rgba(74,222,128,.18) }
.orb__lede{ margin:13px 0 0; font-size:clamp(14.5px,1.05vw,15.5px);
  line-height:1.48; color:var(--dim); letter-spacing:-.006em }
.orb__cta{ display:flex; flex-wrap:wrap; gap:10px; margin-top:17px }
.orb__proof{ display:flex; align-items:center; gap:12px; margin-top:17px }
.orb__avatars{ display:flex }
.orb__avatars img{ width:30px; height:30px; border-radius:999px; margin-left:-9px;
  border:2px solid var(--bg); object-fit:cover; display:block }
.orb__avatars img:first-child{ margin-left:0 }
.orb__proof .orb__stars{ display:flex; gap:2px; color:#f5b301; font-size:12.5px; line-height:1 }
.orb__proof .orb__txt{ font-size:13px; color:var(--faint); letter-spacing:-.004em; margin-top:5px }

@media (max-width:980px){ .orb__links{ display:none } }
@media (max-width:900px){
  .orb-root{ position:relative; inset:auto; min-height:100dvh; overflow-y:visible;
    display:flex; flex-direction:column }
  .orb__stage{ position:relative; inset:auto; order:3; width:100%;
    flex:1 1 auto; min-height:min(42dvh,340px) }
  .orb__nav{ order:1 }
  .orb__band{ display:contents }
  .orb__lead{ order:2; padding:clamp(6px,2vh,18px) var(--pad) 0;
    font-size:clamp(36px,9.2vw,50px) }
  .orb__hint{ order:4; margin:clamp(6px,1.4vh,14px) auto 0 }
  .orb__side{ order:5; justify-self:auto; max-width:none;
    padding:clamp(14px,2.6vh,26px) var(--pad) clamp(24px,4vh,40px) }
  .orb__lede{ max-width:46ch }
}
@media (max-width:420px){ .orb__navend .sign{ display:none } }
@media (prefers-reduced-motion:reduce){ .orb__btn,.orb__btn .orb__arrow,.orb__hint{ transition:none } }
`;

/* ---------------- deterministic rng ---------------- */
type Rng = () => number;

function mulberry32(a: number): Rng {
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const pick = <T,>(r: Rng, a: readonly T[]): T =>
  a[Math.min(a.length - 1, (r() * a.length) | 0)];
const rr = (r: Rng, a: number, b: number) => a + r() * (b - a);

/* ---------------- atlas ---------------- */
const TW = 384,
  TH = 256,
  COLS = 12,
  ROWS = 8,
  TILES = COLS * ROWS;

/* ---------------- sphere of cards ---------------- */
const SPHERE = { R: 1, nEquator: 20, latLimit: 84, gap: 0.1 };
const ASPECTS = [1.62, 1.56, 1.5, 1.5, 1.5, 1.44, 1.38, 1.32];

type Vec3 = [number, number, number];

interface Card {
  lat: number;
  lon: number;
  rad: number;
  w: number;
  h: number;
  roll: number;
  tile: number;
  basis?: { n: Vec3; R: Vec3; U: Vec3 };
  outline?: Array<[number, number]>;
  vBase?: number;
}

function buildCards(): Card[] {
  const r = mulberry32(424242);
  const out: Card[] = [];
  const lim = (SPHERE.latLimit * Math.PI) / 180;
  const cellEq = (2 * Math.PI) / SPHERE.nEquator;
  const nRings = Math.max(1, Math.round((lim * 2) / (cellEq / 1.5)));
  const pitch = (lim * 2) / nRings;
  for (let j = 0; j <= nRings; j++) {
    const lat = -lim + j * pitch;
    const cl = Math.max(0.05, Math.cos(lat));
    const n = Math.max(1, Math.round(SPHERE.nEquator * cl));
    const cellW = (2 * Math.PI * cl) / n;
    const cellH = pitch;
    const maxW = cellW * (1 - SPHERE.gap);
    const maxH = cellH * (1 - SPHERE.gap);
    const off = r() * Math.PI * 2;
    for (let i = 0; i < n; i++) {
      const asp = pick(r, ASPECTS);
      const roll = rr(r, -0.045, 0.045);
      const ca = Math.cos(roll);
      const sa = Math.abs(Math.sin(roll));
      let w = Math.min(maxW / (ca + sa / asp), maxH / (ca / asp + sa));
      w *= rr(r, 0.86, 0.96);
      const h = w / asp;
      const slackLon = Math.max(0, (cellW - (w * ca + h * sa)) / 2);
      out.push({
        lat,
        lon: off + (i / n) * Math.PI * 2 + (slackLon / cl) * rr(r, -0.85, 0.85),
        rad: SPHERE.R * (1 + rr(r, 0, 0.02)),
        w,
        h,
        roll,
        tile: 0,
      });
    }
  }
  const idx = out.map((_, i) => i);
  for (let i = idx.length - 1; i > 0; i--) {
    const k = (r() * (i + 1)) | 0;
    [idx[i], idx[k]] = [idx[k], idx[i]];
  }
  idx.forEach((o, i) => {
    out[o].tile = i % TILES;
  });
  const dir = out.map((c) => {
    const cl = Math.cos(c.lat);
    return [cl * Math.sin(c.lon), Math.sin(c.lat), cl * Math.cos(c.lon)] as const;
  });
  const MIND = Math.cos(0.62);
  const clash = (i: number) => {
    for (let j = 0; j < out.length; j++) {
      if (j === i || out[j].tile !== out[i].tile) continue;
      const d = dir[i][0] * dir[j][0] + dir[i][1] * dir[j][1] + dir[i][2] * dir[j][2];
      if (d > MIND) return true;
    }
    return false;
  };
  for (let pass = 0; pass < 4; pass++) {
    for (let i = 0; i < out.length; i++) {
      if (!clash(i)) continue;
      for (let t = 0; t < 24; t++) {
        const k = (r() * out.length) | 0;
        if (k === i) continue;
        const a = out[i].tile;
        const b = out[k].tile;
        out[i].tile = b;
        out[k].tile = a;
        if (!clash(i) && !clash(k)) break;
        out[i].tile = a;
        out[k].tile = b;
      }
    }
  }
  return out;
}

function cardOutline(w: number, h: number, rad: number, seg: number): Array<[number, number]> {
  const a = w / 2,
    b = h / 2,
    q = Math.min(rad, a * 0.9, b * 0.9);
  const pts: Array<[number, number]> = [];
  const corners = [
    [a - q, b - q, 0],
    [-a + q, b - q, Math.PI / 2],
    [-a + q, -b + q, Math.PI],
    [a - q, -b + q, -Math.PI / 2],
  ];
  for (const [cx, cy, a0] of corners) {
    for (let s = 0; s <= seg; s++) {
      const t = a0 + (s / seg) * (Math.PI / 2);
      pts.push([cx + Math.cos(t) * q, cy + Math.sin(t) * q]);
    }
  }
  return pts;
}

const SEG = 7;
const PER = 4 * (SEG + 1);

function cardBasis(c: Card): { n: Vec3; R: Vec3; U: Vec3 } {
  const cl = Math.cos(c.lat),
    sl = Math.sin(c.lat),
    cs = Math.cos(c.lon),
    sn = Math.sin(c.lon);
  const n: Vec3 = [cl * sn, sl, cl * cs];
  const u: Vec3 = [-sl * sn, cl, -sl * cs];
  const g: Vec3 = [
    u[1] * n[2] - u[2] * n[1],
    u[2] * n[0] - u[0] * n[2],
    u[0] * n[1] - u[1] * n[0],
  ];
  const cr = Math.cos(c.roll),
    sr = Math.sin(c.roll);
  return {
    n,
    R: [g[0] * cr + u[0] * sr, g[1] * cr + u[1] * sr, g[2] * cr + u[2] * sr],
    U: [u[0] * cr - g[0] * sr, u[1] * cr - g[1] * sr, u[2] * cr - g[2] * sr],
  };
}

function writeCard(pos: Float32Array, c: Card, scale: number, radMul: number) {
  const b = c.basis!;
  const rad = c.rad * radMul;
  const ox = b.n[0] * rad,
    oy = b.n[1] * rad,
    oz = b.n[2] * rad;
  let p = c.vBase! * 3;
  pos[p++] = ox;
  pos[p++] = oy;
  pos[p++] = oz;
  for (let i = 0; i < c.outline!.length; i++) {
    const x = c.outline![i][0] * scale;
    const y = c.outline![i][1] * scale;
    pos[p++] = ox + b.R[0] * x + b.U[0] * y;
    pos[p++] = oy + b.R[1] * x + b.U[1] * y;
    pos[p++] = oz + b.R[2] * x + b.U[2] * y;
  }
}

function buildGeometry(cards: Card[]) {
  const vCount = cards.length * (PER + 1);
  const pos = new Float32Array(vCount * 3);
  const uv = new Float32Array(vCount * 2);
  const col = new Float32Array(vCount * 3).fill(1);
  const idx = new Uint32Array(cards.length * PER * 3);
  const TILEU = 1 / COLS,
    TILEV = 1 / ROWS,
    INSET = 0.5 / TW;
  let up = 0,
    ip = 0,
    vbase = 0;

  for (const c of cards) {
    c.basis = cardBasis(c);
    c.outline = cardOutline(c.w, c.h, c.w * 0.065, SEG);
    c.vBase = vbase;
    writeCard(pos, c, 1, 1);

    const cl = c.tile % COLS,
      row = (c.tile / COLS) | 0;
    const asp = c.w / c.h,
      tileAsp = TW / TH;
    const us = asp > tileAsp ? 1 : asp / tileAsp;
    const vs = asp > tileAsp ? tileAsp / asp : 1;
    uv[up++] = (cl + 0.5) * TILEU;
    uv[up++] = (row + 0.5) * TILEV;
    for (let i = 0; i < c.outline.length; i++) {
      const lu = 0.5 + (c.outline[i][0] / c.w) * us;
      const lv = 0.5 + (c.outline[i][1] / c.h) * vs;
      uv[up++] = (cl + Math.min(1 - INSET, Math.max(INSET, lu))) * TILEU;
      uv[up++] = (row + 1 - Math.min(1 - INSET, Math.max(INSET, lv))) * TILEV;
    }
    for (let i = 0; i < PER; i++) {
      idx[ip++] = vbase;
      idx[ip++] = vbase + 1 + i;
      idx[ip++] = vbase + 1 + ((i + 1) % PER);
    }
    vbase += PER + 1;
  }

  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  const colAttr = new THREE.BufferAttribute(col, 3);
  g.setAttribute("color", colAttr);
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 1.35);
  return { g, basePos: pos, colAttr };
}

/* ================================================================
   React component
   ================================================================ */

export function OrbGallery() {
  const stageRef = useRef<HTMLDivElement>(null);
  const hintRef = useRef<HTMLDivElement>(null);
  const navRef = useRef<HTMLElement>(null);
  const leadRef = useRef<HTMLHeadingElement>(null);
  const sideRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const stageEl = stage;
    let cancelled = false;

    const canvas = document.createElement("canvas");
    canvas.className = "orb__canvas";
    stageEl.appendChild(canvas);

    const hintEl = hintRef.current;
    const navEl = navRef.current;
    const leadEl = leadRef.current;
    const sideEl = sideRef.current;

    const canHover =
      !window.matchMedia || window.matchMedia("(hover:hover) and (pointer:fine)").matches;
    const reduce =
      window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const HOVER_POP = 1.12;
    const AUTO = (Math.PI * 2) / 20;

    const stacked = () => window.innerWidth <= 900;

    let renderer: THREE.WebGLRenderer | null = null;
    let scene: THREE.Scene | null = null;
    let camera: THREE.PerspectiveCamera | null = null;
    let orbGroup: THREE.Group | null = null;
    let atlasTex: THREE.CanvasTexture | null = null;
    let cardMesh: THREE.Mesh | null = null;
    let geo: THREE.BufferGeometry | null = null;
    let basePos: Float32Array | null = null;
    let posAttr: THREE.BufferAttribute | null = null;
    let colAttr: THREE.BufferAttribute | null = null;
    let cards: Card[] = [];
    let hoverT: Float32Array | null = null;

    let yaw = 0,
      pitch = 0,
      yawVel = 0,
      pitchVel = 0,
      dragging = false,
      lastPointer: { x: number; y: number } | null = null;
    let hoverPos: { x: number; y: number } | null = null;
    let hoverIdx = -1,
      dimT = 0,
      slowT = 0;
    const live = new Set<number>();
    let fitW = 0,
      fitH = 0;

    const raycaster = new THREE.Raycaster();
    const ndc = new THREE.Vector2();
    const hoverBall = new THREE.Sphere(new THREE.Vector3(), 1.06);
    const hitPt = new THREE.Vector3();

    function clearTo(cx: number, cy: number, el: HTMLElement | null) {
      if (!el) return 0;
      const r = el.getBoundingClientRect();
      const dx = Math.max(r.left - cx, 0, cx - r.right);
      const dy = Math.max(r.top - cy, 0, cy - r.bottom);
      return Math.hypot(dx, dy);
    }

    function fitCamera(force?: boolean) {
      if (!renderer || !camera || !orbGroup) return;
      const W = stageEl.clientWidth;
      const H = stageEl.clientHeight;
      if (W < 2 || H < 2) return;
      if (!force && W === fitW && H === fitH) return;
      fitW = W;
      fitH = H;
      const D = 4.0;
      const alpha = Math.asin(1 / D);
      let diameter: number;
      if (stacked()) {
        diameter = Math.min(0.92 * W, 0.96 * H);
      } else {
        const cx = W / 2,
          cy = H / 2;
        let R = Math.min(0.3 * W, 0.46 * H);
        R = Math.min(R, clearTo(cx, cy, navEl) - 18);
        R = Math.min(R, clearTo(cx, cy, hintEl) - 18);
        R = Math.min(R, clearTo(cx, cy, leadEl) - 18);
        R = Math.min(R, clearTo(cx, cy, sideEl) - 18);
        diameter = 2 * Math.max(70, R);
      }
      const halfFov = Math.atan(Math.tan(alpha) * (H / diameter));
      camera.fov = Math.max(4, Math.min(100, (halfFov * 2 * 180) / Math.PI));
      camera.aspect = W / H;
      camera.position.set(0, 0, D);
      camera.updateProjectionMatrix();
      orbGroup.position.y = 0;
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(W, H, false);
    }

    function bindPointer() {
      const rad = () => Math.min(canvas.clientWidth, canvas.clientHeight) || 1;
      canvas.addEventListener("pointerdown", (e: PointerEvent) => {
        dragging = true;
        hintEl?.classList.add("gone");
        canvas.classList.add("dragging");
        canvas.setPointerCapture(e.pointerId);
        lastPointer = { x: e.clientX, y: e.clientY };
      });
      canvas.addEventListener("pointermove", (e: PointerEvent) => {
        if (canHover && e.pointerType !== "touch") {
          const b = canvas.getBoundingClientRect();
          hoverPos = {
            x: ((e.clientX - b.left) / b.width) * 2 - 1,
            y: -((e.clientY - b.top) / b.height) * 2 + 1,
          };
        }
        if (!dragging || !lastPointer) return;
        const dx = e.clientX - lastPointer.x,
          dy = e.clientY - lastPointer.y;
        lastPointer = { x: e.clientX, y: e.clientY };
        const k = 2.6 / rad();
        yaw += dx * k;
        yawVel = dx * k * 60 * 0.35;
        pitch = Math.max(-0.26, Math.min(0.26, pitch + dy * k * 0.55));
        pitchVel = dy * k * 60 * 0.2;
      });
      const end = (e: PointerEvent) => {
        if (!dragging) return;
        dragging = false;
        canvas.classList.remove("dragging");
        lastPointer = null;
        try {
          canvas.releasePointerCapture(e.pointerId);
        } catch {
          /* noop */
        }
      };
      canvas.addEventListener("pointerup", end);
      canvas.addEventListener("pointercancel", end);
      canvas.addEventListener("pointerleave", (e: PointerEvent) => {
        hoverPos = null;
        end(e);
      });
    }

    function updateHover(dt: number) {
      if (!hoverT || !camera || !cardMesh || !orbGroup) return;
      let want = -1;
      if (hoverPos && !dragging && canHover) {
        ndc.set(hoverPos.x, hoverPos.y);
        raycaster.setFromCamera(ndc, camera);
        hoverBall.center.copy(orbGroup.position);
        if (raycaster.ray.intersectsSphere(hoverBall)) {
          const hit = raycaster.intersectObject(cardMesh, false)[0];
          if (hit && hit.faceIndex !== undefined) want = Math.floor(hit.faceIndex / PER);
          else if (hoverIdx >= 0) want = hoverIdx;
          else if (raycaster.ray.intersectSphere(hoverBall, hitPt)) {
            orbGroup.worldToLocal(hitPt).normalize();
            let best = -1,
              bd = -2;
            for (let i = 0; i < cards.length; i++) {
              const n = cards[i].basis!.n;
              const dd = n[0] * hitPt.x + n[1] * hitPt.y + n[2] * hitPt.z;
              if (dd > bd) {
                bd = dd;
                best = i;
              }
            }
            want = best;
          }
        }
      }
      if (want !== hoverIdx) {
        if (hoverIdx >= 0) live.add(hoverIdx);
        if (want >= 0) live.add(want);
        hoverIdx = want;
      }

      const ease = 1 - Math.pow(0.0009, dt);
      dimT += ((hoverIdx >= 0 ? 1 : 0) - dimT) * ease;
      slowT += ((hoverIdx >= 0 ? 1 : 0) - slowT) * ease;
      const dimTo = 1 - 0.42 * dimT;
      (cardMesh.material as THREE.MeshBasicMaterial).color.setScalar(dimTo);

      let movedGeo = false,
        movedCol = false;
      for (const i of Array.from(live)) {
        const target = i === hoverIdx ? 1 : 0;
        const t = hoverT[i] + (target - hoverT[i]) * ease;
        hoverT[i] = Math.abs(t - target) < 0.0015 ? target : t;
        const c = cards[i],
          k = 1 + hoverT[i] * (HOVER_POP - 1);
        if (basePos) writeCard(basePos, c, k, k);
        movedGeo = true;
        const lift = 1 + hoverT[i] * (1 / dimTo - 1);
        if (colAttr) {
          const arr = colAttr.array as Float32Array;
          const v0 = c.vBase! * 3,
            v1 = v0 + (PER + 1) * 3;
          for (let v = v0; v < v1; v++) arr[v] = lift;
        }
        movedCol = true;
        if (hoverT[i] === 0 && i !== hoverIdx) live.delete(i);
      }
      if (movedGeo && posAttr) posAttr.needsUpdate = true;
      if (movedCol && colAttr) colAttr.needsUpdate = true;
    }

    function initGL() {
      renderer = new THREE.WebGLRenderer({
        canvas,
        antialias: true,
        alpha: true,
        powerPreference: "high-performance",
      });
      renderer.outputEncoding = THREE.sRGBEncoding;
      renderer.setClearColor(0x000000, 0);
      scene = new THREE.Scene();
      camera = new THREE.PerspectiveCamera(19, 1, 0.1, 60);

      atlasTex = new THREE.CanvasTexture(atlasCanvas);
      atlasTex.flipY = false;
      atlasTex.encoding = THREE.sRGBEncoding;
      atlasTex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
      atlasTex.minFilter = THREE.LinearMipmapLinearFilter;
      atlasTex.magFilter = THREE.LinearFilter;
      atlasTex.generateMipmaps = true;
      atlasTex.needsUpdate = true;

      cards = buildCards();
      hoverT = new Float32Array(cards.length);
      const built = buildGeometry(cards);
      geo = built.g;
      basePos = built.basePos;
      colAttr = built.colAttr;
      posAttr = geo.getAttribute("position") as THREE.BufferAttribute;

      const mat = new THREE.MeshBasicMaterial({
        map: atlasTex,
        side: THREE.FrontSide,
        vertexColors: true,
        toneMapped: false,
      });
      cardMesh = new THREE.Mesh(geo, mat);
      orbGroup = new THREE.Group();
      orbGroup.add(cardMesh);
      scene.add(orbGroup);

      fitCamera();
      const ro = new ResizeObserver(() => fitCamera());
      ro.observe(stageEl);
      const onResize = () => fitCamera(true);
      window.addEventListener("resize", onResize);
      bindPointer();
      return { ro, onResize };
    }

    let rafId = 0;
    let prev = performance.now();
    function tick(now: number) {
      if (cancelled) return;
      rafId = requestAnimationFrame(tick);
      let dt = (now - prev) / 1000;
      prev = now;
      if (dt > 0.1) dt = 0.1;
      fitCamera();
      if (!dragging) {
        yaw += (AUTO * (reduce ? 0 : 1) * (1 - 0.78 * slowT) + yawVel) * dt;
        yawVel *= Math.pow(0.0016, dt);
        pitch += pitchVel * dt;
        pitchVel *= Math.pow(0.0016, dt);
        pitch *= Math.pow(0.22, dt);
      }
      if (orbGroup) orbGroup.rotation.set(pitch, yaw, 0);
      updateHover(dt);
      if (renderer && scene && camera) renderer.render(scene, camera);
    }

    const atlasCanvas = document.createElement("canvas");
    atlasCanvas.width = TW * COLS;
    atlasCanvas.height = TH * ROWS;

    let cleanup: (() => void) | null = null;
    (async () => {
      const ac = atlasCanvas.getContext("2d");
      if (ac) {
        ac.fillStyle = "#f4f4f5";
        ac.fillRect(0, 0, atlasCanvas.width, atlasCanvas.height);
        const imgs = await Promise.all(
          TILE_SRC.map(
            (src) =>
              new Promise<HTMLImageElement | null>((res) => {
                const im = new Image();
                im.onload = () => res(im);
                im.onerror = () => res(null);
                im.src = src;
              })
          )
        );
        imgs.forEach((im, i) => {
          if (!im) return;
          ac.drawImage(im, (i % COLS) * TW, ((i / COLS) | 0) * TH, TW, TH);
        });
      }
      if (cancelled) return;
      const ctxLost = () => {
        cancelled = true;
        cancelAnimationFrame(rafId);
      };
      canvas.addEventListener("webglcontextlost", ctxLost);
      cleanup = () => {
        cancelled = true;
        cancelAnimationFrame(rafId);
        canvas.removeEventListener("webglcontextlost", ctxLost);
        const c = initGL();
        c.ro.disconnect();
        window.removeEventListener("resize", c.onResize);
        if (renderer) {
          renderer.dispose();
          renderer.forceContextLoss();
        }
        if (geo) geo.dispose();
        if (atlasTex) atlasTex.dispose();
        canvas.remove();
      };
      initGL();
      rafId = requestAnimationFrame(tick);
    })();

    return () => {
      if (cleanup) cleanup();
      else cancelled = true;
    };
  }, []);

  return (
    <div className="orb-root">
      <style dangerouslySetInnerHTML={{ __html: CSS }} />

      <header className="orb__nav" ref={navRef}>
        <a className="orb__logo" href="#">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.4">
            <path d="M4.5 9.5v-2a2 2 0 0 1 2-2h11a2 2 0 0 1 2 2v2" />
            <path d="M4.5 9.5h15v2.6a7.5 7.5 0 0 1-7.5 7.5 7.5 7.5 0 0 1-7.5-7.5v-2.6Z" />
            <path d="M12 12v4.6M9.9 13.7h4.2" />
          </svg>
          FamilyVault
        </a>
        <nav className="orb__links">
          <a href="#vault">Vault</a>
          <a href="#tree">Tree</a>
          <a href="#pod">Pod</a>
        </nav>
        <div className="orb__navend">
          <Link className="sign" href="/login">
            Sign in
          </Link>
          <Link className="orb__btn sm solid" href="/sign-up">
            Get started
          </Link>
        </div>
      </header>

      <div className="orb__stage" ref={stageRef} aria-hidden="true" />

      <div className="orb__hint" ref={hintRef} aria-hidden="true">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.7"
          strokeLinejoin="round"
          strokeLinecap="round"
        >
          <path d="M7.2 2.9 L16.4 10.6 L11.6 11.2 L13.9 15.5 L11.6 16.7 L9.3 12.4 L6.6 15.3 Z" />
          <path d="M12 17.3 v2.2" />
          <ellipse cx="12" cy="20.5" rx="5.4" ry="1.7" />
        </svg>
        Drag to spin &middot; hover a memory
      </div>

      <section className="orb__band">
        <h1 className="orb__lead" ref={leadRef}>
          Every memory,
          <br />
          safely <em>kept</em>.
        </h1>

        <div className="orb__side" ref={sideRef}>
          <span className="orb__badge">
            <i></i>
            Multi-tenant &middot; AI-augmented &middot; RLS protected
          </span>
          <p className="orb__lede">
            Your family&rsquo;s photos, health records and milestone capsules &mdash;
            classified by biometrics, sealed under three tiers of privacy, and woven
            into one living family tree.
          </p>
          <div className="orb__cta">
            <Link className="orb__btn lg solid" href="/sign-up">
              Create your family vault
            </Link>
            <Link className="orb__btn lg ghost" href="/login">
              Open the demo <span className="orb__arrow">&rarr;</span>
            </Link>
          </div>
          <div className="orb__proof">
            <div className="orb__avatars">
              {[0, 1, 2, 3, 4].map((i) => (
                <AvatarImage key={i} i={i} />
              ))}
            </div>
            <div>
              <div className="orb__stars" aria-hidden="true">
                &#9733;&#9733;&#9733;&#9733;&#9733;
              </div>
              <div className="orb__txt">Joined by families across generations</div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function AvatarImage({ i }: { i: number }) {
  const src = AVATARS[i] as string | undefined;
  if (!src) return null;
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt="" />;
}