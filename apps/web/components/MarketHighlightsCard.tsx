'use client';

import { SkeletonStats } from './SkeletonLoader';
import type { ApiExchangeRate, ApiMarketOverviewResponse, ApiPriceHistoryPoint } from '@/lib/api';
import { Locale } from '@/lib/i18n';

type Props = {
  msg: any; // i18n messages
  marketOverview: ApiMarketOverviewResponse | null;
  locale: Locale;
  formatDateTimeInBrazil: (date: string | Date, locale: Locale) => string;
  formatAssetValueSummary: (asset: any, locale: Locale) => string;
  formatCurrency: (value: number, currency: string, locale: Locale) => string;
};

export function MarketHighlightsCard({
  msg,
  marketOverview,
  locale,
  formatDateTimeInBrazil,
  formatAssetValueSummary,
  formatCurrency
}: Props) {
  if (!marketOverview) {
    return <SkeletonStats />;
  }

  return (
    <div className="card highlights-card">
      <div className="highlights-header">
        <div>
          <h3>{msg.marketHighlights}</h3>
          <p className="muted highlights-summary">
            {msg.daySummary}: {locale === "pt-BR" ? "ativos monitorados" : "tracked assets"} {marketOverview.summary.asset_count} • {locale === "pt-BR" ? "ao vivo" : "live"} {marketOverview.summary.live_asset_count} • {locale === "pt-BR" ? "fallback" : "fallback"} {marketOverview.summary.fallback_asset_count}
          </p>
        </div>
        <p className="muted highlights-updated" suppressHydrationWarning>
          {formatDateTimeInBrazil(marketOverview.summary.updated_at, locale)} ({locale === "pt-BR" ? "UTC-3" : "UTC-3"})
        </p>
      </div>

      <div className="highlights-grid">
        {marketOverview.featured_assets.map((asset) => (
          <article key={`${asset.exchange}-${asset.symbol}`} className="highlight-tile">
            <p className="muted highlight-kicker">{asset.exchange}</p>
            <strong>{asset.symbol}</strong>
            <p>{asset.name}</p>
            <p className="muted">
              {formatAssetValueSummary(asset, locale)}
            </p>
          </article>
        ))}
      </div>

      <div className="highlights-bottom">
        <div className="headline-block">
          <h4>{msg.mainHeadline}</h4>
          {marketOverview.headline ? (
            <a href={marketOverview.headline.url} target="_blank" rel="noreferrer" className="news-title">
              {marketOverview.headline.title}
            </a>
          ) : (
            <p className="muted">{msg.noNews}</p>
          )}
        </div>
        <div className="currencies-block">
          <h4>{msg.keyCurrencies}</h4>
          <div className="currency-list">
            {(marketOverview.currency_rates as ApiExchangeRate[]).filter((rate) => rate.base_currency !== "BRL").map((rate) => (
              <div key={`${rate.base_currency}-${rate.quote_currency}`} className="currency-chip">
                <strong>{rate.base_currency}/{rate.quote_currency}</strong>
                <span>{formatCurrency(rate.rate, rate.quote_currency, locale)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
