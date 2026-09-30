import Link from "next/link";
import { KbcLogo } from "./KbcLogo";

export function SiteHeader() {
  return (
    <header className="relative z-10 border-b border-kbc-night-100/60 bg-white/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1320px] items-center justify-between px-6">
        <Link href="/" className="press flex items-center gap-3" aria-label="KBC Fit home">
          <KbcLogo className="h-8 w-auto" />
          <span className="h-6 w-px bg-kbc-night-100" aria-hidden />
          <span className="text-[17px] font-bold tracking-tight text-kbc-night">
            Fit
          </span>
        </Link>
        <nav className="flex items-center gap-1 text-sm font-semibold">
          <Link
            href="/"
            className="press rounded-full px-4 py-2 text-kbc-night-300 hover:bg-kbc-night-25 hover:text-kbc-night"
          >
            Personas
          </Link>
          <Link
            href="/demo/lucas"
            className="press rounded-full bg-kbc-night px-4 py-2 text-white hover:bg-kbc-night-600"
          >
            Try the demo
          </Link>
        </nav>
      </div>
    </header>
  );
}
