import type { PersonaId } from "@/lib/engine/types";

/**
 * Persona photography. Synthetic, generated portraits — no real customers.
 *
 * Both files per persona are derived from one source image: the studio white is
 * trimmed off, `figure` is the standing figure and `face` a square head crop.
 * Regenerate with `scripts/personas.mjs`.
 *
 * To pair a persona with a different photo, swap the file names here — nothing
 * else refers to them.
 */
export type PersonaImage = {
  figure: string;
  figureWidth: number;
  figureHeight: number;
  face: string;
  /** Tint the figure stands against on the home cards. Matches the avatar tone. */
  tint: string;
};

export const PERSONA_IMAGES: Record<PersonaId, PersonaImage> = {
  lucas: {
    figure: "/personas/lucas.webp",
    figureWidth: 217,
    figureHeight: 640,
    face: "/personas/lucas-face.webp",
    tint: "#e5f4ff",
  },
  julie: {
    figure: "/personas/julie.webp",
    figureWidth: 211,
    figureHeight: 640,
    face: "/personas/julie-face.webp",
    tint: "#fdecee",
  },
  marc: {
    figure: "/personas/marc.webp",
    figureWidth: 244,
    figureHeight: 640,
    face: "/personas/marc-face.webp",
    tint: "#e6f4f1",
  },
  claire: {
    figure: "/personas/claire.webp",
    figureWidth: 250,
    figureHeight: 640,
    face: "/personas/claire-face.webp",
    tint: "#fff7d6",
  },
};
