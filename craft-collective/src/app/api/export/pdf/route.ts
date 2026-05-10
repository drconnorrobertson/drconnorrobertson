import { NextResponse } from "next/server";
import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import { Phorest, PhorestClientError, type PhorestSale } from "@/lib/phorest";
import { env } from "@/lib/env";
import { parseRange } from "@/lib/dates";
import { summariseSales } from "@/lib/reports";
import { isAuthed } from "@/lib/auth";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function fmtCurrency(n: number): string {
  return n.toLocaleString("en-IE", { style: "currency", currency: "EUR" });
}

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
    const summary = summariseSales(sales);

    const doc = await PDFDocument.create();
    const font = await doc.embedFont(StandardFonts.Helvetica);
    const bold = await doc.embedFont(StandardFonts.HelveticaBold);
    let pageRef = doc.addPage([595, 842]); // A4
    const { height } = pageRef.getSize();
    let y = height - 60;
    const left = 50;
    const black = rgb(0.1, 0.1, 0.1);
    const muted = rgb(0.4, 0.4, 0.4);

    const drawText = (
      text: string,
      opts?: { size?: number; font?: typeof font; color?: typeof black },
    ) => {
      pageRef.drawText(text, {
        x: left,
        y,
        size: opts?.size ?? 11,
        font: opts?.font ?? font,
        color: opts?.color ?? black,
      });
    };

    const lineBreak = (n = 16) => {
      y -= n;
      if (y < 60) {
        pageRef = doc.addPage([595, 842]);
        y = pageRef.getSize().height - 60;
      }
    };

    drawText("Craft Collective — Sales Report", { size: 20, font: bold });
    lineBreak(24);
    drawText(`Range: ${from} to ${to}`, { color: muted });
    lineBreak();
    drawText(`Branch: ${branchId}`, { color: muted });
    lineBreak(24);

    drawText(`Total revenue: ${fmtCurrency(summary.totalRevenue)}`, { font: bold });
    lineBreak();
    drawText(`Sale count: ${summary.saleCount}`);
    lineBreak();
    drawText(`Average sale: ${fmtCurrency(summary.averageSale)}`);
    lineBreak(28);

    drawText("By staff", { font: bold, size: 13 });
    lineBreak(20);
    if (summary.byStaff.length === 0) {
      drawText("(no sales in range)", { color: muted });
      lineBreak();
    } else {
      for (const row of summary.byStaff.slice(0, 30)) {
        drawText(
          `${row.staffName.padEnd(28)}  ${row.count.toString().padStart(4)}  ${fmtCurrency(row.revenue)}`,
        );
        lineBreak();
      }
    }
    lineBreak(12);

    drawText("By day", { font: bold, size: 13 });
    lineBreak(20);
    for (const row of summary.byDay) {
      drawText(
        `${row.date}    ${row.count.toString().padStart(4)}    ${fmtCurrency(row.revenue)}`,
      );
      lineBreak();
    }

    const bytes = await doc.save();

    return new Response(Buffer.from(bytes), {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Disposition": `attachment; filename="sales-${from}-to-${to}.pdf"`,
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
