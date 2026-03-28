'use client';

import { Locale } from '@/lib/i18n';

type ThemePreference = "system" | "light" | "dark";

type Props = {
  msg: any; // i18n messages
  locale: Locale;
  themePreference: ThemePreference;
  isAuthenticated: boolean;
  readOnlyMode: boolean;
  isOffline: boolean;
  onLocaleChange: (locale: Locale) => void;
  onThemeChange: (theme: ThemePreference) => void;
  loginAnonymously: () => void;
};

export function SettingsCard({
  msg,
  locale,
  themePreference,
  isAuthenticated,
  readOnlyMode,
  isOffline,
  onLocaleChange,
  onThemeChange,
  loginAnonymously
}: Props) {
  return (
    <div className="card">
      <h3>{msg.settings}</h3>
      <label>
        {msg.language}: {" "}
        <select
          value={locale}
          disabled={readOnlyMode}
          onChange={(e) => onLocaleChange(e.target.value as Locale)}
        >
          <option value="pt-BR">Português (Brasil)</option>
          <option value="en">English</option>
        </select>
      </label>
      <label style={{ marginLeft: "0.75rem" }}>
        {msg.theme}: {" "}
        <select
          value={themePreference}
          disabled={readOnlyMode}
          onChange={(e) => onThemeChange(e.target.value as ThemePreference)}
        >
          <option value="system">{msg.themeSystem}</option>
          <option value="light">{msg.themeLight}</option>
          <option value="dark">{msg.themeDark}</option>
        </select>
      </label>
      <p className="muted" style={{ marginTop: "0.75rem" }}>
        {isAuthenticated
          ? locale === "pt-BR"
            ? "Sessão Supabase ativa."
            : "Supabase session is active."
          : locale === "pt-BR"
            ? "Sem sessão ativa."
            : "No active session."}
      </p>
      {!isAuthenticated ? (
        <button onClick={loginAnonymously} disabled={isOffline || readOnlyMode}>
          {locale === "pt-BR" ? "Entrar anonimamente" : "Sign in anonymously"}
        </button>
      ) : null}
    </div>
  );
}
