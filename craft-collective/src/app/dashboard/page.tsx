import { Suspense } from "react";
import { Phorest, PhorestClientError } from "@/lib/phorest";
import { env } from "@/lib/env";
import { defaultRange } from "@/lib/dates";
import { summariseSales } from "@/lib/reports";
import { isAuthed } from "@/lib/auth";
import { MetricCard } from "@/components/MetricCard";
import { SalesChart } from "@/components/SalesChart";
import { DashboardControls } from "@/components/DashboardControls";
import { SignInForm } from "@/components/SignInForm";

export const dynamic = "force-dynamic";

function fmtCurrency(n: number): string {
  return n.toLocaleString("en-IE", { style: "currency", currency: "EUR" });
}

interface SearchParams {
  from?: string;
  to?: string;
  branchId?: string;
}

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  if (!(await isAuthed())) {
    return (
      <main className="mx-auto max-w-md px-6 py-16">
        <h1 className="text-2xl font-semibold">Sign in</h1>
        <p className="mt-2 text-sm text-neutral-500">
          This dashboard is protected. Enter the shared app password.
        </p>
        <div className="mt-6">
          <SignInForm />
        </div>
      </main>
    );
  }

  const params = await searchParams;
  const fallback = defaultRange();
  const from = params.from ?? fallback.from;
  const to = params.to ?? fallback.to;

  let errorMessage: string | null = null;
  let branches: { branchId: string; name: string }[] = [];
  let summary = summariseSales([]);
  let branchId = params.branchId ?? env.phorestBranchId ?? "";

  try {
    const phorest = new Phorest();
    branches = await phorest.listBranches();
    if (!branchId && branches.length > 0) {
      branchId = branches[0].branchId;
    }
    if (branchId) {
      const sales: Awaited<ReturnType<typeof phorest.listSales>>["content"] = [];
      let page = 0;
      while (page < 25) {
        const res = await phorest.listSales({
          branchId,
          from,
          to,
          page,
          size: 200,
        });
        sales.push(...res.content);
        if (res.content.length < 200) break;
        if (res.totalPages !== undefined && page + 1 >= res.totalPages) break;
        page += 1;
      }
      summary = summariseSales(sales);
    }
  } catch (err) {
    errorMessage =
      err instanceof PhorestClientError
        ? `Phorest error (${err.status}): ${err.message}`
        : err instanceof Error
          ? err.message
          : "Unknown error";
  }

  return (
    <main className="mx-auto max-w-5xl px-6 py-10">
      <header className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Sales dashboard
          </h1>
          <p className="text-sm text-neutral-500">
            {from} → {to}
          </p>
        </div>
      </header>

      <Suspense>
        <DashboardControls
          initialBranches={branches}
          defaultFrom={from}
          defaultTo={to}
          defaultBranchId={branchId}
        />
      </Suspense>

      {errorMessage ? (
        <div className="mt-6 rounded-md border border-red-300 bg-red-50 p-4 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
          {errorMessage}
        </div>
      ) : null}

      <section className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <MetricCard
          label="Total revenue"
          value={fmtCurrency(summary.totalRevenue)}
        />
        <MetricCard label="Sales" value={String(summary.saleCount)} />
        <MetricCard
          label="Average sale"
          value={fmtCurrency(summary.averageSale)}
        />
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-neutral-500">
          Revenue by day
        </h2>
        <div className="rounded-lg border border-neutral-200 p-3 dark:border-neutral-800">
          <SalesChart data={summary.byDay} />
        </div>
      </section>

      <section className="mt-8">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-widest text-neutral-500">
          By staff
        </h2>
        <div className="overflow-x-auto rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead className="bg-neutral-50 text-left text-xs uppercase tracking-wider text-neutral-500 dark:bg-neutral-900">
              <tr>
                <th className="px-4 py-2">Staff</th>
                <th className="px-4 py-2">Sales</th>
                <th className="px-4 py-2">Revenue</th>
              </tr>
            </thead>
            <tbody>
              {summary.byStaff.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-neutral-500">
                    No sales in this range.
                  </td>
                </tr>
              ) : (
                summary.byStaff.map((row) => (
                  <tr
                    key={row.staffName}
                    className="border-t border-neutral-200 dark:border-neutral-800"
                  >
                    <td className="px-4 py-2">{row.staffName}</td>
                    <td className="px-4 py-2">{row.count}</td>
                    <td className="px-4 py-2">{fmtCurrency(row.revenue)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
