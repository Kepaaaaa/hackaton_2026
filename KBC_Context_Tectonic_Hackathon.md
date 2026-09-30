# KBC Fit: MVP and Presentation

> **Today the app shows the same blocks to everyone. KBC Fit shows each customer the one thing that is useful to them, with a number and a reason. When nothing is useful, it says so.**

## 1. The problem

Kate is already proactive: KBC reports personalised suggestions in more than 140 situations, with customer consent. Our reading (an inference, not a confirmed fact) is that these situations are triggers built one by one.

What the brief asks for: understand the customer's situation, adapt the experience automatically, and do it for 2.3 million customers without writing a new trigger for every case. Today's generic blocks (loan, insurance, savings) are identical for a 24-year-old and a retiree.

## 2. Our answer

An engine that:

1. **reads** signals, with the customer's consent;
2. **measures a gap** (something missing, or money sitting idle);
3. **decides** with rules, not with a language model;
4. **composes** the screen: a quantified goal, the reason, and a next step;
5. **shows nothing** when nothing is useful.

| | What we do |
|---|---|
| **Understand** | Weighted signals (transactions, products held, situation **declared** by the customer). A gap and a confidence score |
| **Adapt** | The screen recomposes per customer. The customer switches off a signal and the screen changes. Without consent, nothing is read |
| **Scale** | A tiny per-customer calculation with no shared state, so it scales horizontally. Adding a case means adding data and a rule |

## 3. The site

```
/  (pick a persona)  →  /demo/[persona]
                              │
                BEFORE screen  +  "Activate KBC Fit" button on the left
                              │  click
                              ▼  fade
                AFTER screen  (interactive)  +  "What KBC Fit changes" panel

/how-it-works   (the explanation page)
/login          (last step, only if we have time, see section 7)
```

All text on the site and in the documentation is in **English**.

### Step 1: pick a persona (`/`)
Four cards: Lucas, Thomas, Monique, Claire. One click opens that persona's demo.

### Step 2: BEFORE screen (`/demo/[persona]`)
- **Centre:** a phone showing the app **as it is today**: the persona's accounts, a payment method, two generic banners (loan, insurance) and the navigation bar. All accounts are **fictional**.
- **Left: a large "Activate KBC Fit" button**, with one line of explanation.

### Step 3: transition
On click, a **fade** (View Transitions API) to the AFTER screen. The left button becomes "Deactivate KBC Fit" so you can go back during the video. The fade is skipped if the user has asked for reduced motion.

### Step 4: AFTER screen (interactive)
1. Greeting and situation chips (age, status, situation, housing)
2. **Goal card:** animated ring, monthly amount, target date
3. **"Why this goal?":** the signals used, each with its own switch
4. **"Next step":** a button that opens a confirmation sheet (simulation only, nothing is subscribed)
5. Collapsed "My accounts" block

**Interactions per persona:**

| Persona | What you can play with |
|---|---|
| **Lucas** | Monthly amount slider: the target date and coverage update live |
| **Thomas** | Monthly amount slider. Switch off "situation you told us about": the proposal disappears |
| **Monique** | Return slider from 0% to 2%: the yearly scenario changes. "Prepare my appointment" button |
| **Claire** | "See what we checked": an expandable list. No action proposed |

**Shared interactions:** signal switches (the card disappears below 60% confidence), a consent switch (nothing is read), and a button to go back to BEFORE.

### Problems panel (right)
- **BEFORE: "What's wrong with today's app".** First what this customer misses, with their own numbers (Lucas reaches only 6% of his goal and is shown a home loan). Then every problem of today's app: no personalisation, offers that don't fit, no number and no reason, data the bank already has but does not use, gaps that go unnoticed, always something to sell, no transparency or control, triggers built one by one that don't scale.
- **AFTER: "What KBC Fit changes".** Each problem flips to its fix, one by one. The confidence score stays visible inside the phone, in "Why this goal?".

## 4. The four personas

| Persona | Situation | What AFTER shows | Next step |
|---|---|---|---|
| **Lucas, 24**: first salary | Stable income, €1,800 savings, no supplementary pension | About **€110/month** to reach €100,000 at 64. Without changing anything: **6%** of the goal | Start pension savings |
| **Thomas, 31**: first child | Child just born, **told us himself**, €2,400 savings | About **€60/month** to reach €20,000 by the child's 18th birthday. Without changing anything: **21%** | Open long-term savings |
| **Monique, 66**: retired | €54,400 on the current account, €2,491 spent a month | **€39,454 sitting idle** above a €14,946 cushion (6 months of her real spending). **73%** of the balance is inactive | Prepare an advisor appointment |
| **Claire, 38**: already well covered | Savings invested, insurance in place, plan active | **Nothing to suggest today** | None |

- "Meuf parfaite" is renamed **"already well covered"** on the site. Easy to change back.
- Amounts use **3% a year, an illustrative assumption, not guaranteed**. These are not KBC rates.
- Lucas and Thomas get an amount capped at 40% of their monthly margin.

## 5. The engine (rules)

```
confidence = sum of the weights of active signals   (weights: 0.30 / 0.45 / 0.25)
no consent                 → nothing is read
no gap (Claire)            → "nothing to suggest"
confidence < 0.60          → card hidden
otherwise                  → card composed
```

- **Savings goal:** the monthly amount needed to reach the target by the horizon, rounded up to the next €10, capped at 40% of the margin.
- **Idle cash:** balance minus a cushion of 6 months of expenses.
- Texts are generated from **templates**. A language model would only rephrase after the decision, with pseudonymised data. It is **not** connected in the MVP.

## 6. Data: Supabase

### What we store
Persona data lives in **Supabase** (Postgres), table `personas`: one row per demo customer, with the record exported from the synthetic bank database (`datasets/export_personas.py`). If we reach the login step, users and audit logs go there too.

**No customer data in the code.** Each persona is built from its database record (`src/lib/engine/profile.ts`): name, age, accounts, chips, signals, the situation (child goal, retirement goal, idle cash or nothing) and every amount. The code only holds product rules (€100,000 at 64, €20,000 at 18, 3% a year, 6-month cushion, signal weights). When Supabase is unreachable, the site uses an offline snapshot of the same records and shows an "Offline snapshot" badge.

| Table | Content |
|---|---|
| `personas` | `id`, `customer_id`, `as_of`, `record` (JSON: profile, accounts, facts, recent transactions) |
| `users` | *(login step only)* username, password **hash**, role, created date |
| `audit_log` | *(login step only)* user, action, persona, date |
| `login_attempts` | *(login step only)* username, date, success |

Schema: `supabase/migrations/`. Data: `supabase/seed.sql`, generated by `node scripts/supabase-seed.mjs`.

### Security
- **Read-only.** RLS is on. The Data API roles (`anon`, `authenticated`) can only `select` on `personas`; insert, update and delete are refused.
- **Server-side only.** The app reads Supabase from the server with the **publishable key**. No secret key is used by the app, and nothing is sent to the browser.
- **Never an error page.** If the project is paused or unreachable, the site falls back to the offline snapshot.

### Environment variables (Vercel only, not Git)
Set automatically by the Supabase integration on Vercel: `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY` (the app only needs these two).
Login step only: `SESSION_SECRET`, `DEMO_USER`, `DEMO_PASSWORD`

## 7. Login: the last step, only if we have time

The core demo does **not** depend on login. Build order:

1. **Core demo** with personas hard-coded in the code (engine, BEFORE/AFTER, interactions, explanation page).
2. **Database:** move persona data to Supabase, with the offline snapshot as fallback.
3. **Login:** only if the first two are done and stable.

If we skip login, the site is public and the data is 100% synthetic, which is fine. Say it clearly in the README.

### If we build it
- Password **never stored in plain text**: **argon2id** or **bcrypt** with a salt.
- Session in an **httpOnly, Secure, SameSite=Lax** cookie, signed (JWT with `jose`) and short-lived.
- **Limit login attempts**, with a neutral error message (never "unknown user").
- **Check the session on every server page and API route**, not only in route protection. This is exactly what Aikido looks for: authentication, authorisation, IDOR.
- Persona data is read **server-side only**, never through a free-form ID from the browser.
- Demo credentials: **nothing in the code, README or committed seed**. The seed script reads `DEMO_USER` and `DEMO_PASSWORD` from the environment. Give a demo account to the judges in the **Builderbase description** (low risk, the data is synthetic) and **test it in a private window** before submitting.
- A login wall can block judges. That is another reason this step comes last.

## 8. Tech stack

| Layer | Choice |
|---|---|
| Framework | Next.js (App Router), React 19, strict TypeScript |
| Styling | Tailwind CSS v4, KBC Design Language tokens (see `docs/kbc-brand.md`) |
| Database | Supabase (Postgres, RLS, read-only Data API) |
| Validation | Zod on every input, including Server Actions |
| Engine | Pure TypeScript module, no dependencies, tested with Vitest |
| Transition | View Transitions API |
| Auth *(last step)* | Server Actions, argon2id or bcrypt, signed session cookie (`jose`) |
| Deployment | Vercel, public GitHub repository |

```
src/
  app/            /, /demo/[persona], /how-it-works, (/login)
  components/     phone Before/After, goal card, signals, problems panel, confirmation sheet
  lib/engine/     types, projection, decision, tests
  lib/data/       Supabase access, offline snapshot
  lib/auth/       (login step) hashing, session, access control
```

## 9. Security (for Aikido)

- **100% synthetic data.** No real data anywhere.
- Inputs validated with Zod. Database access only on the server.
- Security headers (CSP, frame-ancestors, referrer policy, content type).
- **No secrets in Git.** Check the Git history before making the repository public.
- If login ships: server-side checks everywhere, attempt limiting, strong hashing, secure cookies.
- Run the Aikido baseline as soon as the core code exists, fix what it finds, re-scan, and screenshot before and after. If the "before" is almost empty, say so in the description instead of planting flaws.

## 10. Rules to respect

- Amounts are simulator assumptions. Products are generic categories. Any investment goes through an advisor.
- No sensitive inference without customer confirmation (Thomas: situation **declared**).
- **No screenshots of the real app** in the repository, the video or Builderbase. Your before/after image shows a real name and real IBANs.
- Public repository, README in English (project, how to run it, what is unfinished).
- KBC branding is allowed (we work with KBC on this challenge): official KBC logo and KBC Design Language (KDL) tokens, see `docs/kbc-brand.md`. Add the mention "Built for the KBC challenge at Tectonic Hackathon".
- The KBC font (Museo Sans) is commercial: never commit the font files. Use it only if installed locally, with Nunito Sans as fallback.

## 11. Video script (under 3 minutes, narrated in English)

| Time | Content |
|---|---|
| 0:00 to 0:20 | Pick Lucas. The BEFORE screen: the same blocks for everyone |
| 0:20 to 0:50 | Click "Activate KBC Fit", fade, the screen recomposes, every problem in the side panel flips to its fix. Move the slider |
| 0:50 to 1:10 | Thomas: the situation is declared, never inferred |
| 1:10 to 1:25 | Monique: €39,454 sitting idle, advisor appointment |
| 1:25 to 1:45 | **Claire: "nothing to suggest"** |
| 1:45 to 2:05 | Switch off a signal, then consent: everything recomposes |
| 2:05 to 2:45 | "How it works" page, scaling argument, Aikido before/after screenshot |

## 12. Split between four people

| | Mission |
|---|---|
| **P1** | Engine: types, projection, decision, tests |
| **P2** | Personas data, BEFORE screen, then Supabase with fallback. Login only at the end |
| **P3** | Front end: phone BEFORE/AFTER, button, fade, interactions, side panel |
| **P4** | Public repo, README, Vercel and variables, explanation page, Aikido, video, submission |

**First sync point:** freeze the format of a persona and of a recommendation.

## 13. Risks and limits

- **Time is the main risk.** A complete demo without database or login beats an unfinished login. Follow the build order in section 7.
- Synthetic data, not a real bank.
- Scalability is **argued, not tested** at 2.3 million customers.
- No language model and no "customers like you" clustering in the MVP.
- This is the most expected angle on the brief. We only win if the pitch stays **"measured benefit, and the right to propose nothing"**.

## 14. To submit on Builderbase

Short description (with the demo account if login ships), video under 3 minutes, link to the public repository with README, Aikido before/after screenshots. No edits after the final submission.
