// Seed Google Cloud Firestore with the four personas exported from the synthetic bank database.
//
//   GCP_PROJECT_ID=... GCP_CLIENT_EMAIL=... GCP_PRIVATE_KEY="..." node scripts/seed-firestore.mjs
//
// Writes personas/{id} with one field `record` (the JSON of src/lib/data/personas.generated.json).
// Credentials come from the environment only, never from a file in Git.
import { createSign } from "node:crypto";
import { readFile } from "node:fs/promises";

const { GCP_PROJECT_ID: project, GCP_CLIENT_EMAIL: email } = process.env;
const key = process.env.GCP_PRIVATE_KEY?.replace(/\\n/g, "\n");
if (!project || !email || !key) {
  console.error("Set GCP_PROJECT_ID, GCP_CLIENT_EMAIL and GCP_PRIVATE_KEY first.");
  process.exit(1);
}

const now = Math.floor(Date.now() / 1000);
const b64 = (o) => Buffer.from(JSON.stringify(o)).toString("base64url");
const unsigned = `${b64({ alg: "RS256", typ: "JWT" })}.${b64({
  iss: email,
  scope: "https://www.googleapis.com/auth/datastore",
  aud: "https://oauth2.googleapis.com/token",
  iat: now,
  exp: now + 3600,
})}`;
const assertion = `${unsigned}.${createSign("RSA-SHA256").update(unsigned).sign(key, "base64url")}`;
const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
  method: "POST",
  headers: { "content-type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({ grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer", assertion }),
});
if (!tokenRes.ok) throw new Error(`token: ${tokenRes.status} ${await tokenRes.text()}`);
const { access_token } = await tokenRes.json();

const data = JSON.parse(await readFile(new URL("../src/lib/data/personas.generated.json", import.meta.url), "utf8"));
for (const [id, record] of Object.entries(data.personas)) {
  const url = `https://firestore.googleapis.com/v1/projects/${project}/databases/(default)/documents/personas/${id}`;
  const res = await fetch(url, {
    method: "PATCH",
    headers: { authorization: `Bearer ${access_token}`, "content-type": "application/json" },
    body: JSON.stringify({
      fields: { record: { stringValue: JSON.stringify(record) }, customerId: { stringValue: record.customerId }, asOf: { stringValue: data.asOf } },
    }),
  });
  console.log(`personas/${id}: ${res.ok ? "ok" : `${res.status} ${await res.text()}`}`);
}
