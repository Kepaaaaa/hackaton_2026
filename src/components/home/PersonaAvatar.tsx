import type { PersonaId } from "@/lib/engine/types";

const TONES: Record<PersonaId, string> = {
  lucas: "bg-kbc-accent-100 text-kbc-accent-600",
  julie: "bg-[#fdecee] text-[#a32a3b]",
  marc: "bg-[#e6f4f1] text-kbc-teal",
  claire: "bg-[#fff7d6] text-[#776100]",
};

export function PersonaAvatar({ id, name, size = "md" }: { id: PersonaId; name: string; size?: "sm" | "md" | "lg" }) {
  const dims = size === "lg" ? "size-14 text-xl" : size === "sm" ? "size-9 text-sm" : "size-12 text-lg";
  return (
    <span aria-hidden className={`inline-grid shrink-0 place-items-center rounded-full font-extrabold ${dims} ${TONES[id]}`}>
      {name.charAt(0)}
    </span>
  );
}
