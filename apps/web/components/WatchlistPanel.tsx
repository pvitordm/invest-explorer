'use client';

import { Locale } from '@/lib/i18n';
import type { ApiWatchlistItem } from '@/lib/api';

type Props = {
  msg: any; // i18n messages
  watchlistItems: ApiWatchlistItem[];
  locale: Locale;
};

export function WatchlistPanel({ msg, watchlistItems, locale }: Props) {
  return (
    <div className="card">
      <h3>{locale === "pt-BR" ? "Watchlist" : "Watchlist"}</h3>
      {watchlistItems.length === 0 ? (
        <p className="muted">
          {locale === "pt-BR"
            ? "Nenhum ativo na watchlist."
            : "No items in watchlist."}
        </p>
      ) : (
        watchlistItems.map((item) => (
          <p key={`${item.asset.exchange}-${item.asset.symbol}-watchlist`}>
            {item.asset.name} <strong>{item.asset.symbol}</strong> • {item.asset.exchange} • {item.asset.currency}
          </p>
        ))
      )}
    </div>
  );
}
