## Invest Explorer (MVP scaffold)

Monorepo structure:

```text
apps/
	api/
		.env.example
		market_data.py
		main.py
		requirements.txt
	web/
		.env.example
		package.json
		tsconfig.json
		next.config.ts
		next-env.d.ts
		app/
			globals.css
			layout.tsx
			manifest.ts
			page.tsx
		components/
			OfflineBanner.tsx
		lib/
			cache.ts
			i18n.ts
```

### API (FastAPI)

```powershell
cd "c:\Users\pedro\OneDrive\Área de Trabalho\sql\invest-explorer\apps\api"
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API runs at `http://localhost:8000`.

### Beta test (local)

1. Ensure Supabase migration was executed.
2. Start API and web.
3. Sign in anonymously in web Settings.
4. Click `Atualizar agora`.
5. Confirm `POST /refresh` stores snapshot with live/fallback metrics.

Windows note for PowerShell script policy (`npm.ps1` blocked):

```powershell
cd "c:\Users\pedro\OneDrive\Área de Trabalho\sql\invest-explorer\apps\web"
& "C:\Users\pedro\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.14.1-win-x64\npm.cmd" install
& "C:\Users\pedro\AppData\Local\Microsoft\WinGet\Packages\OpenJS.NodeJS.LTS_Microsoft.Winget.Source_8wekyb3d8bbwe\node-v24.14.1-win-x64\npm.cmd" run build
```

### Supabase migration (Step 1)

Run the SQL file in Supabase SQL Editor:

- `supabase/migrations/20260325_000001_init_mvp.sql`

This creates MVP tables + RLS policies:

- `assets`
- `watchlists`
- `watchlist_items`
- `portfolio_positions`
- `snapshots`

### Web (Next.js)

```powershell
cd "c:\Users\pedro\OneDrive\Área de Trabalho\sql\invest-explorer\apps\web"
Copy-Item .env.example .env.local
npm install
npm run dev
```

Web runs at `http://localhost:3000`.

### Notes

- `pt-BR` is the default locale; `en` is secondary via a Settings toggle.
- Offline mode shows a banner and uses cached `last_snapshot` from IndexedDB.
- API includes `GET /health`, real Supabase JWT verification via JWKS, `GET /watchlist`, and `POST /refresh`.
- `GET /watchlist` now reads real Supabase data (creates a default watchlist for the user if missing).
- `POST /refresh` now builds curated market snapshot (~20 assets) with live/fallback prices and BRL valuation conversion.
- Web now reads Supabase session and sends `Bearer <access_token>` to API for `GET /watchlist` and `POST /refresh`.
- Web supports anonymous sign-in button (requires Anonymous Auth enabled in Supabase).
- Offline mode is strict read-only on web: write actions are disabled and UI shows a read-only state.
- Web also caches and displays `last_viewed_assets` via IndexedDB.

# invest-explorer
