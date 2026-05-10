"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface SalesChartDatum {
  date: string;
  revenue: number;
}

export function SalesChart({ data }: { data: SalesChartDatum[] }) {
  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 16, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="rgba(127,127,127,0.15)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11 }}
            tickMargin={6}
            interval="preserveStartEnd"
          />
          <YAxis tick={{ fontSize: 11 }} width={48} />
          <Tooltip
            contentStyle={{
              fontSize: 12,
              borderRadius: 6,
              border: "1px solid rgba(127,127,127,0.3)",
            }}
            formatter={(v) =>
              typeof v === "number" ? v.toLocaleString() : String(v)
            }
          />
          <Bar dataKey="revenue" fill="#7aa2f7" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
