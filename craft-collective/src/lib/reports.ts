import type { PhorestSale } from "./phorest";

export interface SalesSummary {
  totalRevenue: number;
  saleCount: number;
  averageSale: number;
  byDay: Array<{ date: string; revenue: number; count: number }>;
  byStaff: Array<{ staffName: string; revenue: number; count: number }>;
}

export function summariseSales(sales: PhorestSale[]): SalesSummary {
  const totalRevenue = sales.reduce((acc, s) => acc + (s.total ?? 0), 0);
  const saleCount = sales.length;
  const averageSale = saleCount > 0 ? totalRevenue / saleCount : 0;

  const dayMap = new Map<string, { revenue: number; count: number }>();
  const staffMap = new Map<string, { revenue: number; count: number }>();

  for (const sale of sales) {
    const day = (sale.date ?? "").slice(0, 10);
    if (day) {
      const cur = dayMap.get(day) ?? { revenue: 0, count: 0 };
      cur.revenue += sale.total ?? 0;
      cur.count += 1;
      dayMap.set(day, cur);
    }
    const staffName = sale.staffName ?? "Unassigned";
    const sCur = staffMap.get(staffName) ?? { revenue: 0, count: 0 };
    sCur.revenue += sale.total ?? 0;
    sCur.count += 1;
    staffMap.set(staffName, sCur);
  }

  const byDay = Array.from(dayMap.entries())
    .map(([date, v]) => ({ date, ...v }))
    .sort((a, b) => a.date.localeCompare(b.date));

  const byStaff = Array.from(staffMap.entries())
    .map(([staffName, v]) => ({ staffName, ...v }))
    .sort((a, b) => b.revenue - a.revenue);

  return { totalRevenue, saleCount, averageSale, byDay, byStaff };
}

export function toCsv(rows: Array<Record<string, string | number>>): string {
  if (rows.length === 0) return "";
  const headers = Array.from(
    rows.reduce<Set<string>>((set, row) => {
      Object.keys(row).forEach((k) => set.add(k));
      return set;
    }, new Set()),
  );
  const escape = (v: string | number): string => {
    const s = String(v ?? "");
    if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
    return s;
  };
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(headers.map((h) => escape(row[h] ?? "")).join(","));
  }
  return lines.join("\n");
}
