import type { ReactNode } from "react";
import { KbcLogo } from "@/components/brand/KbcLogo";
import { BellIcon, HomeIcon, KateIcon, MoreIcon, PayIcon, ProductsIcon } from "./icons";

export function StatusBar({ tone = "light" }: { tone?: "light" | "dark" }) {
  const color = tone === "light" ? "text-white" : "text-kbc-night";
  return (
    <div className={`flex h-[50px] items-end justify-between px-8 pb-1.5 text-[14px] font-bold ${color}`} aria-hidden>
      <span className="tabular">9:41</span>
      <span className="flex items-center gap-1.5">
        <svg viewBox="0 0 18 12" className="h-3 w-[18px]" fill="currentColor">
          <rect x="0" y="8" width="3" height="4" rx="1" />
          <rect x="5" y="5.5" width="3" height="6.5" rx="1" />
          <rect x="10" y="3" width="3" height="9" rx="1" />
          <rect x="15" y="0" width="3" height="12" rx="1" />
        </svg>
        <svg viewBox="0 0 27 13" className="h-3 w-[26px]" fill="none" stroke="currentColor">
          <rect x="0.5" y="0.5" width="22" height="12" rx="3.5" opacity="0.5" />
          <rect x="2.5" y="2.5" width="16" height="8" rx="2" fill="currentColor" stroke="none" />
          <path d="M24.5 4.5v4" strokeWidth="1.5" strokeLinecap="round" opacity="0.5" />
        </svg>
      </span>
    </div>
  );
}

export function AppHeader({ title, subtitle, badge }: { title: string; subtitle?: string; badge?: ReactNode }) {
  return (
    <div className="bg-kbc-night pb-5 text-white">
      <StatusBar />
      <div className="flex items-center justify-between px-5 pt-3">
        <KbcLogo tone="white" className="h-7 w-auto" />
        <div className="flex items-center gap-2">
          {badge}
          <span className="grid size-9 place-items-center rounded-full bg-white/10">
            <BellIcon className="size-[18px]" />
          </span>
        </div>
      </div>
      <div className="px-5 pt-5">
        <p className="text-[24px] font-extrabold leading-tight tracking-[-0.01em]">{title}</p>
        {subtitle ? <p className="mt-1 text-[14px] text-kbc-night-150">{subtitle}</p> : null}
      </div>
    </div>
  );
}

const TABS = [
  { label: "Home", Icon: HomeIcon },
  { label: "Pay", Icon: PayIcon },
  { label: "Products", Icon: ProductsIcon },
  { label: "Kate", Icon: KateIcon },
  { label: "More", Icon: MoreIcon },
];

export function TabBar() {
  return (
    <nav
      aria-label="App navigation (illustration)"
      className="absolute inset-x-0 bottom-0 z-20 grid grid-cols-5 border-t border-kbc-night-100/70 bg-white/95 px-2 pb-6 pt-2 backdrop-blur"
    >
      {TABS.map(({ label, Icon }, i) => (
        <span
          key={label}
          className={`flex flex-col items-center gap-0.5 text-[10.5px] font-bold ${i === 0 ? "text-kbc-accent" : "text-kbc-night-300"}`}
        >
          <Icon className="size-[22px]" />
          {label}
        </span>
      ))}
    </nav>
  );
}

export function SectionTitle({ children, action }: { children: ReactNode; action?: ReactNode }) {
  return (
    <div className="mb-2.5 mt-6 flex items-baseline justify-between px-1">
      <h3 className="text-[15px] font-extrabold text-kbc-night">{children}</h3>
      {action}
    </div>
  );
}
