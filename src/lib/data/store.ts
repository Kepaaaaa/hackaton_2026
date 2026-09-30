import { createSign } from "node:crypto";
import type { Persona, PersonaId } from "@/lib/engine/types";
import { type PersonaRecord, withDatabase } from "./fromDatabase";
import { DATABASE_RECORDS, PERSONA_IDS, getSeedPersona } from "./personas";

// Persona data from Google Cloud Firestore (collection `personas`, one document per persona, field `record`
// holding the JSON exported from the synthetic bank database). Server-side only, service account from env.
// Any failure (no credentials, expired hackathon key, network) falls back to the bundled export, so the site
// never shows an error because of the database.

const TIMEOUT_MS = 2500;
let token: { value: string; expires: number } | null = null;

function credentials() {
  const projectId = process.env.GCP_PROJECT_ID;
  const clientEmail = process.env.GCP_CLIENT_EMAIL;
  const privateKey = process.env.GCP_PRIVATE_KEY?.replace(/\\n/g, "\n");
  return projectId && clientEmail && privateKey ? { projectId, clientEmail, privateKey } : null;
}

async function accessToken(clientEmail: string, privateKey: string): Promise<string> {
  if (token && token.expires > Date.now() + 60_000) return token.value;
  const now = Math.floor(Date.now() / 1000);
  const b64 = (o: object) => Buffer.from(JSON.stringify(o)).toString("base64url");
  const unsigned = `${b64({ alg: "RS256", typ: "JWT" })}.${b64({
    iss: clientEmail,
    scope: "https://www.googleapis.com/auth/datastore",
    aud: "https://oauth2.googleapis.com/token",
    iat: now,
    exp: now + 3600,
  })}`;
  const signature = createSign("RSA-SHA256").update(unsigned).sign(privateKey, "base64url");
  const res = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion: `${unsigned}.${signature}` }),
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  if (!res.ok) throw new Error(`token ${res.status}`);
  const body = (await res.json()) as { access_token: string; expires_in: number };
  token = { value: body.access_token, expires: Date.now() + body.expires_in * 1000 };
  return token.value;
}

async function fromFirestore(): Promise<Partial<Record<PersonaId, PersonaRecord>> | null> {
  const c = credentials();
  if (!c) return null;
  try {
    const bearer = await accessToken(c.clientEmail, c.privateKey);
    const url = `https://firestore.googleapis.com/v1/projects/${encodeURIComponent(c.projectId)}/databases/(default)/documents/personas?pageSize=20`;
    const res = await fetch(url, {
      headers: { authorization: `Bearer ${bearer}` },
      signal: AbortSignal.timeout(TIMEOUT_MS),
      next: { revalidate: 300 },
    });
    if (!res.ok) throw new Error(`firestore ${res.status}`);
    const body = (await res.json()) as { documents?: { name: string; fields?: { record?: { stringValue?: string } } }[] };
    const out: Partial<Record<PersonaId, PersonaRecord>> = {};
    for (const doc of body.documents ?? []) {
      const id = doc.name.split("/").pop() as PersonaId;
      const raw = doc.fields?.record?.stringValue;
      if ((PERSONA_IDS as readonly string[]).includes(id) && raw) out[id] = JSON.parse(raw) as PersonaRecord;
    }
    return out;
  } catch (err) {
    console.warn(`[personas] Firestore unavailable, using bundled data: ${(err as Error).message}`);
    return null;
  }
}

export type DataSource = "firestore" | "bundled";

export async function loadPersonas(): Promise<{ personas: Persona[]; source: DataSource }> {
  const remote = await fromFirestore();
  const personas = PERSONA_IDS.map((id) => withDatabase(getSeedPersona(id), remote?.[id] ?? DATABASE_RECORDS[id]));
  const source: DataSource = remote && PERSONA_IDS.every((id) => remote[id]) ? "firestore" : "bundled";
  return { personas, source };
}

export async function loadPersona(id: PersonaId): Promise<Persona> {
  const { personas } = await loadPersonas();
  return personas.find((p) => p.id === id) ?? withDatabase(getSeedPersona(id), DATABASE_RECORDS[id]);
}
