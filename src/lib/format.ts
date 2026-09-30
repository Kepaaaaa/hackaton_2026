const eurFormat = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const eurCentsFormat = new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", minimumFractionDigits: 2 });
const monthYearFormat = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });

export const eur = (n: number) => eurFormat.format(n);
export const eurCents = (n: number) => eurCentsFormat.format(n);
export const pct = (x: number, digits = 0) => `${(x * 100).toFixed(digits)}%`;
export const monthYear = (iso: string) => monthYearFormat.format(new Date(`${iso}T00:00:00Z`));
export const maskedIban = (last4: string) => `BE•• •••• •••• ${last4}`;
