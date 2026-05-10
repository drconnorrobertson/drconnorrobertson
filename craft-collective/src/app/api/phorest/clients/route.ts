import { NextResponse } from "next/server";
import { Phorest, PhorestClientError } from "@/lib/phorest";
import { isAuthed } from "@/lib/auth";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  if (!(await isAuthed())) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }
  const url = new URL(req.url);
  const page = Number(url.searchParams.get("page") ?? 0);
  const size = Math.min(Number(url.searchParams.get("size") ?? 50), 200);
  const branchId = url.searchParams.get("branchId") ?? undefined;
  try {
    const result = await new Phorest().listClients({ page, size, branchId });
    return NextResponse.json(result);
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
