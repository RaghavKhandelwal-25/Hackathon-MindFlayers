# AI Financial Coach – frontend (Stages 1–7 + service layer)
npm install && cp .env.example .env && npm run dev
Set VITE_USE_MOCK=false once the Python backend is up. All API contracts live in src/services/*.js
(expected response shapes are documented as comments). Mock code is isolated in services/api.js and the USE_MOCK branches.
