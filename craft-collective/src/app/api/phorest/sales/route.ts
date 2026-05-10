import { NextResponse } from "next/server";
import { Phorest, PhorestClientError, type PhorestSale } from "@/lib/phorest";
import { env } from "@/lib/env";
import { parseRange } from "@/lib/dates";
import { summariseSales } from "@/lib/reports";
import { isAuthed } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  if (!(await isAuthed())) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const url = new URL(req.url);
  const { from, to } = parseRange(url.searchParams);
  const branchId =
    url.searchParams.get("branchId") ?? env.phorestBranchId ?? null;
  if (!branchId) {
    return NextResponse.json(
      { error: "branchId is required (pass ?branchId=... or set PHOREST_BRANCH_ID)" },
      { status: 400 },
    );
  }

  try {
    const phorest = new Phorest();
    const sales: PhorestSale[] = [];
    const pageSize = 200;
    let page = 0;
    // Cap pages to avoid runaway loops on large date ranges.
    while (page < 25) {
      const res = await phorest.listSales({
        branchId,
        from,
        to,
        page,
        size: pageSize,
      });
      sales.push(...res.content);
      if (res.content.length < pageSize) break;
      if (res.totalPages !== undefined && page + 1 >= res.totalPages) break;
      page += 1;
    }

    return NextResponse.json({
      range: { from, to },
      branchId,
      sales,
      summary: summariseSales(sales),
    });
  } catch (err) {
    if (err instanceof PhorestClientError) {
      return NextResponse.json(
        { error: err.message, status: err.status, body: err.body },
        { status: 502 },
      );
    }
    throw err;
  }
}
