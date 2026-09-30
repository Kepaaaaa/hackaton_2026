import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.8,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export const HomeIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4.5v-5.5h-5V20H5a1 1 0 0 1-1-1z" />
  </svg>
);
export const PayIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M4 8h13l-3-3M20 16H7l3 3" />
  </svg>
);
export const ProductsIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <rect x="4" y="4" width="7" height="7" rx="1.5" />
    <rect x="13" y="4" width="7" height="7" rx="1.5" />
    <rect x="4" y="13" width="7" height="7" rx="1.5" />
    <rect x="13" y="13" width="7" height="7" rx="1.5" />
  </svg>
);
export const KateIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M5 17.5V7a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2H9z" />
    <path d="M9 10.5h.01M12 10.5h.01M15 10.5h.01" strokeWidth="2.6" />
  </svg>
);
export const MoreIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </svg>
);
export const ChevronIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="m9 6 6 6-6 6" />
  </svg>
);
export const BellIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15zM10 20.5a2.2 2.2 0 0 0 4 0" />
  </svg>
);
export const CheckIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="m5 12.5 4.5 4.5L19 7.5" />
  </svg>
);
export const LockIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <rect x="5" y="10.5" width="14" height="10" rx="2" />
    <path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" />
  </svg>
);
export const SparkIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M12 3.5v4M12 16.5v4M3.5 12h4M16.5 12h4M6 6l2.5 2.5M15.5 15.5 18 18M18 6l-2.5 2.5M8.5 15.5 6 18" />
  </svg>
);
export const HouseLoanIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M3.5 11 12 4l8.5 7M6 9.5V20h12V9.5" />
    <path d="M10 20v-5h4v5" />
  </svg>
);
export const ShieldIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <path d="M12 3.5 19 6v5.5c0 4.3-3 7.8-7 9-4-1.2-7-4.7-7-9V6z" />
  </svg>
);
export const CalendarIcon = (p: IconProps) => (
  <svg {...base} {...p}>
    <rect x="4" y="5.5" width="16" height="14.5" rx="2" />
    <path d="M4 10h16M8.5 3.5v4M15.5 3.5v4" />
  </svg>
);
