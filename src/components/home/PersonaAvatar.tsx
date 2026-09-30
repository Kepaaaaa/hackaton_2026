import Image from "next/image";
import { PERSONA_IMAGES } from "@/lib/data/personaImages";
import type { PersonaId } from "@/lib/engine/types";

const TONES: Record<PersonaId, string> = {
  lucas: "bg-kbc-accent-100 text-kbc-accent-600",
  julie: "bg-[#fdecee] text-[#a32a3b]",
  marc: "bg-[#e6f4f1] text-kbc-teal",
  claire: "bg-[#fff7d6] text-[#776100]",
};

const SIZES: Record<"sm" | "md" | "lg", { box: string; px: string }> = {
  sm: { box: "size-9 text-sm", px: "36px" },
  md: { box: "size-12 text-lg", px: "48px" },
  lg: { box: "size-14 text-xl", px: "56px" },
};

export function PersonaAvatar({
  id,
  name,
  size = "md",
}: {
  id: PersonaId;
  name: string;
  size?: "sm" | "md" | "lg";
}) {
  const { box, px } = SIZES[size];
  return (
    <span
      aria-hidden
      className={`relative inline-grid shrink-0 place-items-center overflow-hidden rounded-full font-extrabold ${box} ${TONES[id]}`}
    >
      {/* The initial shows through if the portrait ever fails to load. */}
      {name.charAt(0)}
      <Image
        src={PERSONA_IMAGES[id].face}
        alt=""
        fill
        sizes={px}
        className="object-cover"
      />
    </span>
  );
}
