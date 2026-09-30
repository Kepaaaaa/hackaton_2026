# KBC Fit

Built for the KBC challenge at Tectonic Hackathon.

KBC Fit shows each customer the one thing that is useful to them, with a number and a reason. When nothing is useful, it says so. All data in this project is 100% synthetic.

## Data: Google Cloud

We use **Google Cloud** for the database.

| Service | What it holds |
|---|---|
| **Firestore** | The app data: the demo personas (profile, signals, accounts) and, if login ships, users and audit logs |
| **BigQuery** | The synthetic ML datasets: customers, accounts, transactions, website/app navigation events, and the ground-truth labels kept in a separate dataset |

- The server reads Google Cloud with a service account. The key lives in Vercel environment variables (`GCP_PROJECT_ID`, `GCP_CLIENT_EMAIL`, `GCP_PRIVATE_KEY`), **never in Git**.
- If Google Cloud is unreachable (for example after the hackathon credentials expire), the app falls back to the seed data bundled in the repository. The site never shows an error page because of the database.
