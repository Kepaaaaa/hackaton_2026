export function SiteFooter() {
  return (
    <footer className="mt-auto border-t border-kbc-night-100/60 bg-white">
      <div className="mx-auto flex max-w-[1320px] flex-col gap-2 px-6 py-6 text-xs text-kbc-night-300 sm:flex-row sm:items-center sm:justify-between">
        <p>Built for the KBC challenge at Tectonic Hackathon 2026.</p>
        <p>
          100% synthetic data. Amounts use 3% a year, an illustrative assumption, not guaranteed. Nothing is subscribed.
        </p>
      </div>
    </footer>
  );
}
