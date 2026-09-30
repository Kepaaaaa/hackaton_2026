import Link from "next/link";
import { SiteFooter } from "@/components/brand/SiteFooter";
import { SiteHeader } from "@/components/brand/SiteHeader";

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main className="mx-auto flex max-w-[640px] flex-1 flex-col items-start justify-center px-6 py-24">
        <p className="text-[12px] font-extrabold uppercase tracking-[0.08em] text-kbc-accent-600">404</p>
        <h1 className="mt-2 text-[36px] font-extrabold leading-tight text-kbc-night">Nothing to show here.</h1>
        <p className="mt-3 text-lg text-kbc-night-300">Like KBC Fit when nothing is useful: we would rather say so.</p>
        <Link href="/" className="press mt-8 rounded-full bg-kbc-accent px-6 py-3 font-extrabold text-white hover:bg-kbc-accent-600">
          Pick a customer
        </Link>
      </main>
      <SiteFooter />
    </>
  );
}
