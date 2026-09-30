import type { DataSource } from "@/lib/data/store";

const dateFormat = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

// Where the customer data on screen comes from: live Supabase, or the offline snapshot of the same database.
export function DataSourceBadge({ source, asOf }: { source: DataSource; asOf: string }) {
  const live = source === "supabase";
  const date = dateFormat.format(new Date(`${asOf}T00:00:00Z`));
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11.5px] font-bold ${
        live ? "bg-kbc-success-25 text-kbc-success-600" : "bg-kbc-warning-25 text-[#8a4a05]"
      }`}
      title={live ? "Read live from Supabase" : "Supabase unreachable: offline snapshot of the same database"}
    >
      <span className={`size-1.5 rounded-full ${live ? "bg-kbc-success" : "bg-kbc-warning"}`} aria-hidden />
      {live ? "Live: Supabase" : "Offline snapshot"} · data as of {date}
    </span>
  );
}
