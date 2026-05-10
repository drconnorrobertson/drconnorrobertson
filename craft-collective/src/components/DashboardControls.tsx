"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

interface Branch {
  branchId: string;
  name: string;
}

export function DashboardControls({
  initialBranches,
  defaultFrom,
  defaultTo,
  defaultBranchId,
}: {
  initialBranches: Branch[];
  defaultFrom: string;
  defaultTo: string;
  defaultBranchId: string;
}) {
  const router = useRouter();
  const params = useSearchParams();
  const [from, setFrom] = useState(defaultFrom);
  const [to, setTo] = useState(defaultTo);
  const [branchId, setBranchId] = useState(defaultBranchId);

  useEffect(() => {
    const pFrom = params.get("from");
    const pTo = params.get("to");
    const pBranch = params.get("branchId");
    if (pFrom) setFrom(pFrom);
    if (pTo) setTo(pTo);
    if (pBranch) setBranchId(pBranch);
  }, [params]);

  const apply = () => {
    const qs = new URLSearchParams();
    qs.set("from", from);
    qs.set("to", to);
    if (branchId) qs.set("branchId", branchId);
    router.push(`/dashboard?${qs.toString()}`);
  };

  const exportHref = (kind: "csv" | "pdf") => {
    const qs = new URLSearchParams();
    qs.set("from", from);
    qs.set("to", to);
    if (branchId) qs.set("branchId", branchId);
    return `/api/export/${kind}?${qs.toString()}`;
  };

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
      <label className="flex flex-col text-xs text-neutral-500">
        Branch
        <select
          value={branchId}
          onChange={(e) => setBranchId(e.target.value)}
          className="mt-1 rounded-md border border-neutral-300 bg-transparent px-2 py-1.5 text-sm dark:border-neutral-700"
        >
          {initialBranches.length === 0 ? (
            <option value="">(no branches)</option>
          ) : null}
          {initialBranches.map((b) => (
            <option key={b.branchId} value={b.branchId}>
              {b.name}
            </option>
          ))}
        </select>
      </label>

      <label className="flex flex-col text-xs text-neutral-500">
        From
        <input
          type="date"
          value={from}
          onChange={(e) => setFrom(e.target.value)}
          className="mt-1 rounded-md border border-neutral-300 bg-transparent px-2 py-1.5 text-sm dark:border-neutral-700"
        />
      </label>

      <label className="flex flex-col text-xs text-neutral-500">
        To
        <input
          type="date"
          value={to}
          onChange={(e) => setTo(e.target.value)}
          className="mt-1 rounded-md border border-neutral-300 bg-transparent px-2 py-1.5 text-sm dark:border-neutral-700"
        />
      </label>

      <button
        onClick={apply}
        className="rounded-md bg-neutral-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-neutral-800 dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-200"
      >
        Apply
      </button>

      <div className="ml-auto flex gap-2">
        <a
          href={exportHref("csv")}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-900"
        >
          Download CSV
        </a>
        <a
          href={exportHref("pdf")}
          className="rounded-md border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-50 dark:border-neutral-700 dark:hover:bg-neutral-900"
        >
          Download PDF
        </a>
      </div>
    </div>
  );
}
