import type { Account } from "@/lib/engine/types";
import { eurCents, maskedIban } from "@/lib/format";
import { ChevronIcon } from "./icons";

const DOT: Record<Account["kind"], string> = {
  current: "bg-kbc-accent",
  savings: "bg-kbc-teal",
  investment: "bg-kbc-yellow",
  pension: "bg-kbc-pink",
};

export function AccountList({ accounts }: { accounts: Account[] }) {
  return (
    <ul className="divide-y divide-kbc-night-100/60 overflow-hidden rounded-kbc bg-white shadow-kbc">
      {accounts.map((a) => (
        <li key={a.id} className="flex items-center gap-3 px-4 py-3.5">
          <span className={`h-9 w-1 rounded-full ${DOT[a.kind]}`} aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="truncate text-[14px] font-bold text-kbc-night">{a.label}</p>
            <p className="tabular text-[12px] text-kbc-night-300">{maskedIban(a.last4)}</p>
          </div>
          <p className="tabular text-[15px] font-extrabold text-kbc-night">{eurCents(a.balance)}</p>
          <ChevronIcon className="size-4 text-kbc-night-200" />
        </li>
      ))}
    </ul>
  );
}
