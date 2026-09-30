import { z } from "zod";
import type { PersonaId } from "@/lib/engine/types";
import snapshot from "./personas.generated.json";
import type { PersonaRecord } from "./fromDatabase";

// The site shows four customers of the synthetic bank database. Nothing about them is written here:
// store.ts reads their records from Supabase, and src/lib/engine/profile.ts builds each persona from its record.

export const PERSONA_IDS = ["lucas", "thomas", "monique", "claire"] as const satisfies readonly PersonaId[];

export const personaIdSchema = z.enum(PERSONA_IDS);

/**
 * Offline snapshot of the same Supabase records (exported by datasets/export_personas.py).
 * Used only when Supabase is not configured or unreachable, so the site never shows a database error.
 */
export const SNAPSHOT = {
  asOf: snapshot.asOf,
  records: snapshot.personas as unknown as Record<PersonaId, PersonaRecord>,
};
