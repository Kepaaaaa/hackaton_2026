import Image from "next/image";
import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="relative z-10 border-b border-kbc-night-100/60 bg-white/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-[1320px] items-center justify-between px-6">
        <Link href="/" className="press flex items-center" aria-label="KBC Fit home">
          <Image src="/brand/kbc-fit-logo.webp" alt="KBC Fit" width={873} height={160} priority className="h-7 w-auto" />
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
