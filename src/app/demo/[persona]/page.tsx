import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SiteFooter } from "@/components/brand/SiteFooter";
import { SiteHeader } from "@/components/brand/SiteHeader";
import { DemoExperience } from "@/components/demo/DemoExperience";
import { PERSONA_IDS, personaIdSchema } from "@/lib/data/personas";
import { loadPersonas } from "@/lib/data/store";

export const dynamicParams = false;
// Persona data is read from Supabase (offline snapshot as fallback) and refreshed every 5 minutes.
export const revalidate = 300;

export function generateStaticParams() {
  return PERSONA_IDS.map((persona) => ({ persona }));
}

export async function generateMetadata({ params }: PageProps<"/demo/[persona]">): Promise<Metadata> {
  const parsed = personaIdSchema.safeParse((await params).persona);
  if (!parsed.success) return {};
  const { personas } = await loadPersonas();
  const persona = personas.find((p) => p.id === parsed.data);
  return persona ? { title: `${persona.firstName} · KBC Fit demo` } : {};
}

export default async function DemoPage({ params }: PageProps<"/demo/[persona]">) {
  const parsed = personaIdSchema.safeParse((await params).persona);
  if (!parsed.success) notFound();

  const data = await loadPersonas();
  const all = data.personas;
  const persona = all.find((p) => p.id === parsed.data);
  if (!persona) notFound();
  const personas = all.map(({ id, firstName, age, tagline }) => ({ id, firstName, age, tagline }));

  return (
    <>
      <SiteHeader />
      <main className="flex-1">
        <DemoExperience key={persona.id} persona={persona} personas={personas} data={{ source: data.source, asOf: data.asOf }} />
      </main>
      <SiteFooter data={data} />
    </>
  );
}
