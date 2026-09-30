// Regenerates the persona portraits in public/personas from the source photos.
//
// The sources are synthetic, generated full-body studio shots on white. They are
// NOT committed (several MB each); point PERSONA_SRC at wherever they live:
//
//   PERSONA_SRC=/path/to/photos node scripts/personas.mjs
//
// For each persona it writes <id>.webp (the standing figure, background keyed to
// transparency) and <id>-face.webp (a square head crop for the avatar circles).

import sharp from "sharp";

const SRC = process.env.PERSONA_SRC ?? "C:/Users/Victor/Downloads";
const OUT = "public/personas";

const files = {
  lucas:  "Image ChatGPT 30 sept. 2026, 20_45_45.png",
  julie:  "Image ChatGPT 30 sept. 2026, 20_45_37.png",
  marc:   "Image ChatGPT 30 sept. 2026, 20_45_29.png",
  claire: "Image ChatGPT 30 sept. 2026, 20_45_14.png",
};

const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);

/**
 * Alpha mask separating the figure from the studio background.
 *
 * Flood fills inward from the borders across near-white, near-grey pixels. Only
 * background reachable from an edge is cleared, so white *clothing* in the middle
 * of the figure keeps its pixels instead of being punched through.
 *
 * The background sits in a tight luminance spike at 252-253 and clothing tops out
 * near 248, so 250 separates them without eating light garments.
 */
function backgroundMask(data, W, H, lumMin = 250, chromaMax = 14) {
  const isBackgroundish = (p) => {
    const r = data[p * 3], g = data[p * 3 + 1], b = data[p * 3 + 2];
    const lum = 0.299 * r + 0.587 * g + 0.114 * b;
    const chroma = Math.max(r, g, b) - Math.min(r, g, b);
    return lum >= lumMin && chroma <= chromaMax;
  };

  const bg = new Uint8Array(W * H);
  const stack = new Int32Array(W * H);
  let top = 0;
  const push = (p) => {
    if (!bg[p] && isBackgroundish(p)) {
      bg[p] = 1;
      stack[top++] = p;
    }
  };

  for (let x = 0; x < W; x++) { push(x); push((H - 1) * W + x); }
  for (let y = 0; y < H; y++) { push(y * W); push(y * W + W - 1); }

  while (top > 0) {
    const p = stack[--top];
    const x = p % W;
    if (x > 0) push(p - 1);
    if (x < W - 1) push(p + 1);
    if (p >= W) push(p - W);
    if (p < W * (H - 1)) push(p + W);
  }
  return bg;
}

/**
 * Bounding box of the visible figure.
 *
 * Computed from the alpha mask rather than sharp's trim(): trim() compares RGB
 * against the corner pixel, and this studio white varies between 250 and 255, so
 * it barely crops at all.
 */
function alphaBounds(alpha, W, H, cutoff = 8) {
  let minX = W, maxX = -1, minY = H, maxY = -1;
  for (let y = 0; y < H; y++) {
    for (let x = 0; x < W; x++) {
      if (alpha[y * W + x] > cutoff) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }
  return { left: minX, top: minY, width: maxX - minX + 1, height: maxY - minY + 1 };
}

/**
 * Row where the figure actually meets the ground.
 *
 * The studio contact shadow is not pure white, so the flood fill leaves it behind
 * as a pale puddle under the feet. Shadow rows only ever reach a darkness of about
 * 16, while any row containing shoes jumps past 80, so scanning up from the bottom
 * for the first genuinely dark row finds the soles.
 */
function groundLine(data, W, H, C, minDark = 45) {
  for (let y = H - 1; y >= 0; y--) {
    for (let x = 0; x < W; x++) {
      const p = (y * W + x) * C;
      if (C === 4 && data[p + 3] <= 40) continue;
      const dark = 255 - (0.299 * data[p] + 0.587 * data[p + 1] + 0.114 * data[p + 2]);
      if (dark > minDark) return y;
    }
  }
  return H - 1;
}

/** Horizontal extent of the figure inside a band, from its alpha. */
function bandExtent(alpha, W, y0, y1) {
  let minX = W, maxX = -1;
  for (let y = y0; y < y1; y++) {
    for (let x = 0; x < W; x++) {
      if (alpha[y * W + x] > 128) {
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
      }
    }
  }
  return { minX, maxX };
}

for (const [id, f] of Object.entries(files)) {
  const { data, info } = await sharp(`${SRC}/${f}`).removeAlpha().raw().toBuffer({ resolveWithObject: true });
  const { width: W, height: H } = info;

  const bg = backgroundMask(data, W, H);
  const alpha = Buffer.alloc(W * H);
  for (let p = 0; p < W * H; p++) alpha[p] = bg[p] ? 0 : 255;

  // Feather the matte by a hair so the silhouette edge is not stair-stepped.
  // blur() promotes a 1-channel buffer to 3 channels, so force it back to
  // greyscale -- otherwise every index into `soft` reads the wrong byte.
  const soft = await sharp(alpha, { raw: { width: W, height: H, channels: 1 } })
    .blur(0.8).toColourspace("b-w").raw().toBuffer();

  // joinChannel supplies the 4th channel directly; ensureAlpha first would make
  // this a 5th channel and leave the real alpha fully opaque.
  const rgba = await sharp(data, { raw: { width: W, height: H, channels: 3 } })
    .joinChannel(soft, { raw: { width: W, height: H, channels: 1 } })
    .png().toBuffer();

  const box = alphaBounds(soft, W, H);

  // Drop the contact shadow so the figure stands on the card, not on a pale puddle.
  const ground = groundLine(data, W, H, 3);
  box.height = Math.min(box.height, ground - box.top + 1);

  const figure = await sharp(rgba).extract(box).png().toBuffer();

  // 1. Full figure for the home cards.
  await sharp(figure)
    .resize({ height: 640, fit: "inside" })
    .webp({ quality: 86, alphaQuality: 90 })
    .toFile(`${OUT}/${id}.webp`);

  // 2. Square head crop for the avatar circles, flattened so the circle stays solid.
  const fAlpha = await sharp(figure).extractChannel(3).raw().toBuffer();
  const { minX, maxX } = bandExtent(fAlpha, box.width, Math.round(box.height * 0.02), Math.round(box.height * 0.10));
  const headCx = (minX + maxX) / 2;
  const headW = maxX - minX;

  const side = Math.round(clamp(headW * 1.55, box.height * 0.14, Math.min(box.width, box.height * 0.28)));
  const left = Math.round(clamp(headCx - side / 2, 0, box.width - side));
  const top = Math.round(clamp(box.height / 15 - side * 0.42, 0, box.height - side));

  await sharp(figure)
    .extract({ left, top, width: side, height: side })
    .resize(400, 400)
    .flatten({ background: "#ffffff" })
    .webp({ quality: 88 })
    .toFile(`${OUT}/${id}-face.webp`);

  console.log(`${id}: figure ${box.width}x${box.height} | head w=${headW} | crop ${side}px @ (${left},${top})`);
}
