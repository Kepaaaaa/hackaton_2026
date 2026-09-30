// The KBC mark (sun over the horizon), scaled up and faded as a quiet backdrop.
export function BrandBackdrop() {
  return (
    <div aria-hidden className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute -top-[280px] right-[-120px] size-[640px] rounded-full bg-kbc-accent/[0.07]" />
      <svg
        className="absolute inset-x-0 top-[250px] bottom-0 h-[calc(100%-250px)] w-full text-kbc-accent/[0.06]"
        viewBox="0 0 1440 260"
        preserveAspectRatio="none"
      >
        <path d="M0 150 C 360 110, 820 70, 1440 60 L1440 260 L0 260 Z" fill="currentColor" />
      </svg>
    </div>
  );
}
