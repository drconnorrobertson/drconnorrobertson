import { Phorest, PhorestClientError, type PhorestSale } from "@/lib/phorest";
import { env } from "@/lib/env";
import { parseRange } from "@/lib/dates";
import { toCsv } from "@/lib/reports";
import { isAuthed } from "@/lib/auth";
import { NextResponse } from "next/server";

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
      { error: "branchId is required" },
      { status: 400 },
    );
  }

  try {
    const phorest = new Phorest();
    const sales: PhorestSale[] = [];
    let page = 0;
    while (page < 50) {
      const res = await phorest.listSales({ branchId, from, to, page, size: 200 });
      sales.push(...res.content);
      if (res.content.length < 200) break;
      if (res.totalPages !== undefined && page + 1 >= res.totalPages) break;
      page += 1;
    }

    const rows = sales.map((s) => ({
      saleId: s.saleId,
      date: s.date,
      total: s.total,
      clientName: s.clientName ?? "",
      staffName: s.staffName ?? "",
      paymentMethod: s.paymentMethod ?? "",
    }));
    const csv = toCsv(rows);

    return new Response(csv, {
      status: 200,
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": `attachment; filename="sales-${from}-to-${to}.csv"`,
      },
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
