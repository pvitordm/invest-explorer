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
};

type HoverData = {
  value: number;
  timeLabel: string;
};

type ChartDatum = {
  time: Time;
  value: number;
};

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

export function InteractivePriceChart({ points, locale, currency }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const areaSeriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const [hoverData, setHoverData] = useState<HoverData | null>(null);

  const data = useMemo(() => toChartData(points), [points]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || chartRef.current) return;

    const chart = createChart(container, {
      width: container.clientWidth,
      height: 300,
      layout: {
        background: { type: ColorType.Solid, color: "#ffffff" },
        textColor: "#3d5068",
        attributionLogo: true
      },
      grid: {
        vertLines: { color: "#edf2f7" },
        horzLines: { color: "#edf2f7" }
      },
      rightPriceScale: {
        borderColor: "#d6e0eb"
      },
      timeScale: {
        borderColor: "#d6e0eb",
        timeVisible: true,
        secondsVisible: false
      },
      localization: {
        locale
      },
      crosshair: {
        vertLine: { color: "#154d84", width: 1 },
        horzLine: { color: "#154d84", width: 1 }
      },
      handleScroll: true,
      handleScale: true
    });

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: "#154d84",
      topColor: "rgba(21, 77, 132, 0.28)",
      bottomColor: "rgba(21, 77, 132, 0.04)",
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
        ? new Date(unix * 1000).toLocaleString(locale)
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
  }, [locale]);

  useEffect(() => {
    const chart = chartRef.current;
    const areaSeries = areaSeriesRef.current;
    if (!chart || !areaSeries) return;

    areaSeries.setData(data);
    if (data.length > 1) {
      chart.timeScale().fitContent();
    }
  }, [data]);

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
