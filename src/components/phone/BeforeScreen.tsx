import type { Persona } from "@/lib/engine/types";
import { AccountList } from "./AccountList";
import { AppHeader, SectionTitle } from "./AppChrome";
import { ChevronIcon, HouseLoanIcon, ShieldIcon } from "./icons";

// Today's app: the same generic blocks for everyone.
export function BeforeScreen({ persona }: { persona: Persona }) {
  const current = persona.accounts.find((a) => a.kind === "current") ?? persona.accounts[0];
  return (
    <div className="h-full overflow-y-auto pb-28 [scrollbar-width:none]">
      <AppHeader title={`Good morning, ${persona.firstName}`} subtitle="Here is your overview" />
      <div className="px-4">
        <SectionTitle action={<span className="text-[13px] font-bold text-kbc-accent">All</span>}>
          My accounts
        </SectionTitle>
        <AccountList accounts={persona.accounts} />

        <SectionTitle>My cards</SectionTitle>
        <div className="relative h-[118px] overflow-hidden rounded-[12px] bg-linear-to-br from-[#0097db] to-[#004f88] p-4 text-white shadow-kbc-raised">
          <div className="absolute -right-8 -top-10 size-36 rounded-full bg-white/10" aria-hidden />
          <p className="text-[12px] font-bold uppercase tracking-[0.12em] text-white/80">Debit card</p>
          <p className="tabular mt-7 text-[16px] font-bold tracking-[0.18em]">•••• {current.last4}</p>
          <p className="absolute bottom-4 right-4 text-[12px] font-extrabold">{persona.firstName.toUpperCase()}</p>
        </div>

        <SectionTitle>For you</SectionTitle>
        <div className="grid gap-3">
          <GenericBanner
            icon={<HouseLoanIcon className="size-6" />}
            title="Dreaming of your own home?"
            text="Discover our home loans and simulate your monthly payment."
          />
          <GenericBanner
            icon={<ShieldIcon className="size-6" />}
            title="Protect what matters"
            text="Home insurance in a few taps. Get a quote today."
          />
        </div>
      </div>
    </div>
  );
}

function GenericBanner({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="flex items-center gap-3.5 rounded-kbc bg-white p-4 shadow-kbc">
      <span className="grid size-11 shrink-0 place-items-center rounded-full bg-kbc-accent-100 text-kbc-accent-600">
        {icon}
      </span>
      <div className="min-w-0 flex-1">
        <p className="text-[14px] font-extrabold text-kbc-night">{title}</p>
        <p className="text-[12.5px] leading-snug text-kbc-night-300">{text}</p>
      </div>
      <ChevronIcon className="size-4 shrink-0 text-kbc-night-200" />
    </div>
  );
}
