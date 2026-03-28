'use client';

import { Locale } from '@/lib/i18n';

type Asset = {
  name: string;
  symbol: string;
  exchange: string;
  currency: string;
};

type Props = {
  msg: any; // i18n messages
  assets: Asset[];
  locale: Locale;
};

export function LastViewedPanel({ msg, assets, locale }: Props) {
  return (
    <div className="card">
      <h3>{msg.lastViewed}</h3>
      {assets.length === 0 ? (
        <p className="muted">
          {locale === "pt-BR"
            ? "Nenhum ativo visto ainda."
            : "No viewed assets yet."}
        </p>
      ) : (
        assets.map((asset) => (
          <p key={`${asset.exchange}-${asset.symbol}-viewed`}>
            {asset.name} <strong>{asset.symbol}</strong> • {asset.exchange} • {asset.currency}
          </p>
        ))
      )}
    </div>
  );
}
