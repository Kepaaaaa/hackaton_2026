import { BrandBackdrop } from "@/components/brand/BrandBackdrop";
import { SiteFooter } from "@/components/brand/SiteFooter";
import { SiteHeader } from "@/components/brand/SiteHeader";
import { PersonaCard } from "@/components/home/PersonaCard";
import { listPersonas } from "@/lib/data/personas";

const PRINCIPLES = [
  { k: "Understand", v: "Weighted signals, read only with consent. A gap and a confidence score." },
  { k: "Adapt", v: "The screen recomposes per customer. Switch off a signal and it changes." },
  { k: "Scale", v: "A tiny calculation per customer, no shared state. A new case is data and a rule." },
];

export default function Home() {
  const personas = listPersonas();
  return (
    <>
      <SiteHeader />
      <main className="relative flex-1">
        <BrandBackdrop />
        <section className="relative mx-auto grid max-w-[1320px] gap-14 px-6 pb-20 pt-16 lg:grid-cols-[1.05fr_1fr] lg:gap-20 lg:pt-24">
          <div className="animate-rise">
            <p className="mb-5 inline-flex items-center gap-2 rounded-full bg-white px-3 py-1.5 text-xs font-bold uppercase tracking-[0.08em] text-kbc-accent-600 shadow-kbc">
              <span className="size-1.5 rounded-full bg-kbc-accent" />
              KBC Fit · concept
            </p>
            <h1 className="text-[38px] font-extrabold leading-[1.04] tracking-[-0.02em] text-kbc-night sm:text-[60px]">
              The one thing
              <br />
              that helps.
              <span className="block text-balance text-kbc-accent">Or nothing at all.</span>
            </h1>
            <p className="mt-7 max-w-[34rem] text-lg leading-relaxed text-kbc-night-300">
              Today the app shows the same blocks to everyone. KBC Fit shows each customer the one useful thing, with a
              number and a reason. When nothing is useful, it says so.
            </p>
            <dl className="mt-10 grid max-w-[36rem] gap-5 border-t border-kbc-night-100 pt-8 sm:grid-cols-3">
              {PRINCIPLES.map((p) => (
                <div key={p.k}>
                  <dt className="text-sm font-extrabold text-kbc-night">{p.k}</dt>
                  <dd className="mt-1.5 text-sm leading-snug text-kbc-night-300">{p.v}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div>
            <h2 className="mb-5 text-sm font-bold uppercase tracking-[0.08em] text-kbc-night-300 animate-fade">
              Pick a customer
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {personas.map((p, i) => (
                <PersonaCard key={p.id} persona={p} index={i} />
              ))}
            </div>
            <p className="mt-5 text-sm text-kbc-night-300">
              Each demo starts on today&apos;s app. Press <strong className="text-kbc-night">Activate KBC Fit</strong>{" "}
              to see the same customer, understood.
            </p>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
