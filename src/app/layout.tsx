import type { Metadata } from "next";
import { Nunito_Sans } from "next/font/google";
import "./globals.css";

// KBC uses Museo Sans (commercial, not committed). Nunito Sans is the free fallback.
const nunito = Nunito_Sans({
  variable: "--font-nunito",
  subsets: ["latin"],
  weight: ["300", "400", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "KBC Fit: the one thing that helps",
  description:
    "A personalisation engine concept for KBC: each customer sees the one useful thing, with a number and a reason. Or nothing at all.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${nunito.variable} h-full`}>
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
