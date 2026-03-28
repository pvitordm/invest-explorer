"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AreaSeries,
  ColorType,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type Time
} from "lightweight-charts";
import type { ApiPriceHistoryPoint } from "@/lib/api";

type Props = {
  points: ApiPriceHistoryPoint[];
  locale: string;
  currency: string;
  theme: "light" | "dark";
  initialVisibleRange?: {
    fromIso: string;
    toIso: string;
  } | null;
};

type HoverData = {
  value: number;
  timeLabel: string;
};

type ChartDatum = {
  time: Time;
  value: number;
};

const BRAZIL_TIMEZONE = "America/Sao_Paulo";

function pickPointValue(point: ApiPriceHistoryPoint): number | null {
  if (typeof point.valuation_brl === "number") return point.valuation_brl;
  if (typeof point.price === "number") return point.price;
  return null;
}

function toChartData(points: ApiPriceHistoryPoint[]): ChartDatum[] {
  return points
    .map((point) => {
      const value = pickPointValue(point);
      if (value === null) return null;
      const ts = Math.floor(new Date(point.collected_at).getTime() / 1000);
      if (!Number.isFinite(ts)) return null;
      return { time: ts as Time, value };
    })
    .filter((item): item is ChartDatum => item !== null)
    .sort((a, b) => Number(a.time) - Number(b.time));
}

function toUnixSeconds(iso: string): number | null {
  const ts = Math.floor(new Date(iso).getTime() / 1000);
  return Number.isFinite(ts) ? ts : null;
}

export function InteractivePriceChart({ points, locale, currency, theme, initialVisibleRange = null }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const areaSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const [hoverData, setHoverData] = useState<HoverData | null>(null);

  const data = useMemo(() => toChartData(points), [points]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || chartRef.current) return;

    const isDark = theme === "dark";

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 300,
      layout: {
        background: { type: ColorType.Solid, color: isDark ? "#111a24" : "#ffffff" },
        textColor: isDark ? "#b7c8db" : "#3d5068",
        attributionLogo: true
      },
      grid: {
        vertLines: { color: isDark ? "#203347" : "#edf2f7" },
        horzLines: { color: isDark ? "#203347" : "#edf2f7" }
      },
      rightPriceScale: {
        borderColor: isDark ? "#2a425a" : "#d6e0eb"
      },
      timeScale: {
        borderColor: isDark ? "#2a425a" : "#d6e0eb",
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: true,
        fixRightEdge: true,
        rightOffset: 0
      },
      localization: {
        locale
      },
      crosshair: {
        vertLine: { color: isDark ? "#8bb8e8" : "#154d84", width: 1 },
        horzLine: { color: isDark ? "#8bb8e8" : "#154d84", width: 1 }
      },
      handleScroll: true,
      handleScale: true
    });

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: isDark ? "#8bb8e8" : "#154d84",
      topColor: isDark ? "rgba(139, 184, 232, 0.34)" : "rgba(21, 77, 132, 0.28)",
      bottomColor: isDark ? "rgba(139, 184, 232, 0.06)" : "rgba(21, 77, 132, 0.04)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: true
    });

    chart.subscribeCrosshairMove((param) => {
      if (!param.time || !param.seriesData.size) {
        setHoverData(null);
        return;
      }

      const row = param.seriesData.get(areaSeries) as { value?: number } | undefined;
      if (!row || typeof row.value !== "number") {
        setHoverData(null);
        return;
      }

      const unix = typeof param.time === "number" ? param.time : null;
      const label = unix
        ? new Intl.DateTimeFormat(locale, {
            dateStyle: "short",
            timeStyle: "medium",
            timeZone: BRAZIL_TIMEZONE,
          }).format(new Date(unix * 1000))
        : "-";

      setHoverData({
        value: row.value,
        timeLabel: label
      });
    });

    const resizeObserver = new ResizeObserver((entries) => {
      const nextWidth = entries[0]?.contentRect?.width;
      if (nextWidth && chartRef.current) {
        chartRef.current.applyOptions({ width: Math.max(280, Math.floor(nextWidth)) });
      }
    });
    resizeObserver.observe(container);

    chartRef.current = chart;
    areaSeriesRef.current = areaSeries;

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
      areaSeriesRef.current = null;
    };
  }, [locale, theme]);

  useEffect(() => {
    const chart = chartRef.current;
    const areaSeries = areaSeriesRef.current;
    if (!chart || !areaSeries) return;

    areaSeries.setData(data);
    if (data.length <= 1) return;

    if (initialVisibleRange?.fromIso && initialVisibleRange?.toIso) {
      const from = toUnixSeconds(initialVisibleRange.fromIso);
      const to = toUnixSeconds(initialVisibleRange.toIso);
      if (from !== null && to !== null && from < to) {
        chart.timeScale().setVisibleRange({
          from: from as Time,
          to: to as Time,
        });
        return;
      }
    }

    chart.timeScale().fitContent();
  }, [data, initialVisibleRange]);

  return (
    <div className="interactive-chart-wrap">
      <div ref={containerRef} className="interactive-chart" />
      {hoverData ? (
        <div className="interactive-chart-tooltip">
          <strong>
            {hoverData.value.toLocaleString(locale, {
              style: "currency",
              currency,
              maximumFractionDigits: currency === "JPY" ? 0 : 2
            })}
          </strong>
          <span>{hoverData.timeLabel}</span>
        </div>
      ) : null}
    </div>
  );
}
