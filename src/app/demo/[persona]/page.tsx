import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { SiteFooter } from "@/components/brand/SiteFooter";
import { SiteHeader } from "@/components/brand/SiteHeader";
import { DemoExperience } from "@/components/demo/DemoExperience";
import { PERSONA_IDS, getPersona, listPersonas, personaIdSchema } from "@/lib/data/personas";

export const dynamicParams = false;

export function generateStaticParams() {
  return PERSONA_IDS.map((persona) => ({ persona }));
}

export async function generateMetadata({ params }: PageProps<"/demo/[persona]">): Promise<Metadata> {
  const parsed = personaIdSchema.safeParse((await params).persona);
  if (!parsed.success) return {};
  return { title: `${getPersona(parsed.data).firstName} · KBC Fit demo` };
}

export default async function DemoPage({ params }: PageProps<"/demo/[persona]">) {
  const parsed = personaIdSchema.safeParse((await params).persona);
  if (!parsed.success) notFound();

  const persona = getPersona(parsed.data);
  const personas = listPersonas().map(({ id, firstName, age, tagline }) => ({ id, firstName, age, tagline }));

  return (
    <>
      <SiteHeader />
      <main className="flex-1">
        <DemoExperience key={persona.id} persona={persona} personas={personas} />
      </main>
      <SiteFooter />
    </>
  );
}
