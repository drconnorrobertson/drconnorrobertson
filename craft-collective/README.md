# Craft Collective Reports

A Next.js app that pulls live data from the **Phorest** third-party API for
**Craft Collective Salon Group** and renders an on-screen dashboard plus
CSV / PDF report exports.

Designed to deploy on **Vercel**.

## Stack

- Next.js 15 (App Router) + React 19 + TypeScript
- Tailwind CSS v4
- recharts (charts)
- pdf-lib (PDF generation, runs in the Node runtime on Vercel)
- Phorest third-party API, HTTP Basic auth

## Project layout

```
craft-collective/
├── src/
│   ├── app/
│   │   ├── page.tsx                # Landing
│   │   ├── dashboard/page.tsx      # Main dashboard (server-rendered)
│   │   └── api/
│   │       ├── auth/route.ts       # Sign in / out
│   │       ├── phorest/{branches,clients,appointments,sales}/route.ts
│   │       └── export/{csv,pdf}/route.ts
│   ├── components/                 # Client components (charts, controls)
│   └── lib/
│       ├── phorest.ts              # API client
│       ├── reports.ts              # Summaries + CSV serializer
│       ├── dates.ts                # Range helpers
│       ├── auth.ts                 # Cookie-based shared-password gate
│       └── env.ts                  # Required env var validation
└── .env.example
```

## Local setup

1. Install dependencies (npm / pnpm / yarn all work):

   ```sh
   cd craft-collective
   npm install
   ```

2. Copy `.env.example` to `.env.local` and fill in your Phorest credentials:

   ```sh
   cp .env.example .env.local
   ```

   Required vars:
   - `PHOREST_USERNAME` — e.g. `global/your-account@example.com`
   - `PHOREST_PASSWORD`
   - `PHOREST_BUSINESS_ID`
   - `PHOREST_BASE_URL` — defaults to `https://platform.phorest.com/third-party-api-server`
   - `APP_PASSWORD` — optional; if set, the dashboard is gated behind it

3. Run the dev server:

   ```sh
   npm run dev
   ```

   Open <http://localhost:3000>.

## Deploying to Vercel

1. Push this repo to GitHub.
2. In Vercel, **Add New → Project**, pick the repo. If the app lives in a
   `craft-collective/` subdirectory, set the **Root Directory** to
   `craft-collective` in the project settings.
3. Framework preset: **Next.js** (auto-detected).
4. Add the env vars from `.env.example` in **Project Settings → Environment
   Variables**. At minimum: `PHOREST_USERNAME`, `PHOREST_PASSWORD`,
   `PHOREST_BUSINESS_ID`. Also set `APP_PASSWORD` to lock the dashboard.
5. Deploy.

There is no GitHub Actions workflow in this repo — Vercel handles CI/CD.

## API endpoints

All endpoints require the auth cookie if `APP_PASSWORD` is set.

| Method | Path                                                  | Purpose                              |
| ------ | ----------------------------------------------------- | ------------------------------------ |
| POST   | `/api/auth`                                           | `{ password }` to sign in            |
| GET    | `/api/phorest/branches`                               | List branches                        |
| GET    | `/api/phorest/clients?page=0&size=50&branchId=...`    | List clients                         |
| GET    | `/api/phorest/appointments?branchId=...&from=&to=`    | List appointments                    |
| GET    | `/api/phorest/sales?branchId=...&from=&to=`           | Sales rows + summary                 |
| GET    | `/api/export/csv?branchId=...&from=&to=`              | CSV download of sales                |
| GET    | `/api/export/pdf?branchId=...&from=&to=`              | PDF sales summary                    |

Date params are `YYYY-MM-DD`. Default range is the last 30 days.

## Security notes

- API credentials are never sent to the browser — every Phorest call happens
  in a route handler or server component.
- `.env.local` is gitignored. Do not commit real credentials.
- The dashboard is protected by a shared `APP_PASSWORD` cookie. Replace with
  a real auth provider (NextAuth, Clerk, etc.) before going to production.
- If you've ever pasted production credentials into a chat, screenshot,
  ticket, or shared doc, ask Phorest to rotate them.

## Extending

The Phorest client in `src/lib/phorest.ts` is intentionally minimal. To add
new endpoints, look at the OpenAPI spec at
`https://platform.phorest.com/third-party-api-server/v3/api-docs` and add a
typed method alongside `listSales` / `listAppointments`. Phorest responses
follow HAL+JSON; the `collectEmbedded` helper extracts the first embedded
collection automatically.
