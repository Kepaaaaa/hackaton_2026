import "server-only";
import { createClient } from "@supabase/supabase-js";
import { personaFromRecord } from "@/lib/engine/profile";
import type { Persona, PersonaId } from "@/lib/engine/types";
import type { PersonaRecord } from "./fromDatabase";
import { PERSONA_IDS, SNAPSHOT } from "./personas";

// Persona records from Supabase (table `personas`, see supabase/migrations). Server-side only, with the
// publishable key: the table is read-only through RLS. Any failure (not configured, project paused, network)
// falls back to the offline snapshot of the same records, so the site never shows a database error.

const TIMEOUT_MS = 2500;

function client() {
  const url = process.env.SUPABASE_URL ?? process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_PUBLISHABLE_KEY ?? process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) return null;
  return createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } });
}

interface Row {
  id: string;
  as_of: string;
  record: PersonaRecord;
}

interface Remote {
  records: Partial<Record<PersonaId, PersonaRecord>>;
  asOf?: string;
}

async function fromSupabase(): Promise<Remote | null> {
  const supabase = client();
  if (!supabase) return null;
  try {
    const { data, error } = await supabase
      .from("personas")
      .select("id, as_of, record")
      .in("id", [...PERSONA_IDS])
      .abortSignal(AbortSignal.timeout(TIMEOUT_MS))
      .returns<Row[]>();
    if (error) throw new Error(error.message);
    const out: Remote = { records: {} };
    for (const row of data ?? []) {
      out.records[row.id as PersonaId] = row.record;
      out.asOf ??= row.as_of;
    }
    return out;
  } catch (err) {
    console.warn(`[personas] Supabase unavailable, using the offline snapshot: ${(err as Error).message}`);
    return null;
  }
}

export type DataSource = "supabase" | "snapshot";

export interface PersonaData {
  personas: Persona[];
  /** "supabase" when every record was read live; "snapshot" when the offline copy was used. */
  source: DataSource;
  /** Date of the data (yyyy-mm-dd). */
  asOf: string;
}

export async function loadPersonas(): Promise<PersonaData> {
  const remote = await fromSupabase();
  const live = remote !== null && PERSONA_IDS.every((id) => remote.records[id]);
  const records = live ? (remote.records as Record<PersonaId, PersonaRecord>) : SNAPSHOT.records;
  return {
    personas: PERSONA_IDS.map((id) => personaFromRecord(id, records[id])),
    source: live ? "supabase" : "snapshot",
    asOf: (live && remote.asOf) || SNAPSHOT.asOf,
  };
}
