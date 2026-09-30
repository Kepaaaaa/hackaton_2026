import { SNAPSHOT } from "@/lib/data/personas";
import { personaFromRecord } from "./profile";
import type { Persona, PersonaId } from "./types";

// Test helper: the persona built from its database record in the offline snapshot.
export function persona(id: PersonaId): Persona {
  return personaFromRecord(id, SNAPSHOT.records[id]);
}
