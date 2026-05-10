import Link from "next/link";

export default function Home() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <h1 className="text-3xl font-semibold tracking-tight">
        Craft Collective Reports
      </h1>
      <p className="mt-3 text-neutral-500">
        Pulls live data from the Phorest API and turns it into dashboards and
        downloadable reports for the Craft Collective Salon Group.
      </p>

      <div className="mt-10 flex flex-wrap gap-3">
        <Link
          href="/dashboard"
          className="inline-flex items-center rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-800 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
        >
          Open dashboard →
        </Link>
        <a
          href="https://platform.phorest.com/third-party-api-server/v3/api-docs"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center rounded-md border border-neutral-300 px-4 py-2 text-sm font-medium hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-900"
        >
          Phorest API docs
        </a>
      </div>

      <section className="mt-12 text-sm text-neutral-500">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-neutral-400">
          What's inside
        </h2>
        <ul className="mt-3 space-y-1 list-disc pl-5">
          <li>Sales summary with daily revenue + per-staff breakdown</li>
          <li>CSV export of raw sales rows</li>
          <li>PDF export of the summary report</li>
          <li>Branch and date-range picker</li>
        </ul>
      </section>
    </main>
  );
}
