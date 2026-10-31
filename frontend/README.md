# Finbot - frontend

React + Vite app. Talks to the backend API at `VITE_API_BASE_URL` (see `.env.example`).

```
npm install
cp .env.example .env     # Windows: copy .env.example .env
npm run dev              # http://localhost:5173
npm run build            # production build in dist/
```

API calls live in `src/services/*.js`. Pages are in `src/pages/`, shared pieces in `src/components/`, `src/context/` and `src/layouts/`.
