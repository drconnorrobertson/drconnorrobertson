import { NextResponse } from "next/server";
import { Phorest, PhorestClientError } from "@/lib/phorest";
import { env } from "@/lib/env";
import { parseRange } from "@/lib/dates";
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
      { error: "branchId is required" },
      { status: 400 },
    );
  }
  try {
    const result = await new Phorest().listAppointments({
      branchId,
      from,
      to,
    });
    return NextResponse.json({ range: { from, to }, branchId, ...result });
  } catch (err) {
    if (err instanceof PhorestClientError) {
      return NextResponse.json(
        { error: err.message, status: err.status },
        { status: 502 },
      );
    }
    throw err;
  }
}
