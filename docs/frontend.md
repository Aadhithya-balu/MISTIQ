# MISTIQ Student Frontend

## Audit decisions

- **Keep:** React 18, TypeScript, Vite, React Router, the existing UI primitives, and Tailwind's base setup.
- **Extend:** reusable application navigation, API-backed student pages, development profile persistence, loading/error/empty states, and responsive styles.
- **Refactor:** the scaffold placeholder pages and global shell styling into the student experience.
- **Remove:** placeholder copy and any client-side values that could be mistaken for real progress or predictions.

## Routes

- `/` redirects to `/dashboard`.
- `/login` is a development entry page, not authentication. It creates a Student through the backend or reconnects with an existing student ID. The ID is stored in local storage.
- Student pages: `/dashboard`, `/practice`, `/progress`, `/mistakes`, and `/profile`.
- Secondary research pages: `/research`, `/research/formula`, and `/research/evaluation`. The Research pages call dedicated `/api/research` endpoints and read current saved model parameters, stored prediction traces, and checked-in Phase 4 evaluation artifacts.

## Component and data flow

```text
StudentProvider (current development profile)
  └── AppLayout (desktop sidebar / mobile bottom navigation)
       ├── Dashboard ── progress, mistakes, latest prediction
       ├── Practice ─── questions → attempt POST → backend feedback
       ├── Progress ─── persisted attempt counts and accuracy
       ├── Mistakes ─── persisted mistake events
       └── Profile ──── persisted learner-state features

Typed API modules → shared fetch/error client → FastAPI /api routes
```

API calls are centralized under `frontend/src/api`. The base URL comes from `VITE_API_URL` and defaults to `/api`; the Vite development server proxies that path to `http://127.0.0.1:8000`. When setting an absolute `VITE_API_URL`, include the `/api` suffix.

The practice page loads its questions from the backend. It submits only student ID, question ID, selected option, response time, and an idempotency key. Correctness and mistake classification come from the backend response. The attempt response includes the correct option and answer text, revealed only after submission. Questions do not currently include authored explanations, so feedback points to the recorded topic without inventing a rationale. The UI does not calculate or fabricate an AMPA result.

## State, loading, and errors

Only the active development student ID is stored globally. Page data stays with its page and is refetched from the server. Each API-backed page has a local loading, empty, and error state. A 409 prediction response becomes an honest insufficient-history state; 503 and network errors receive student-friendly copy. Raw stack traces are never displayed.

Prediction probabilities are shown only when the backend status is `NORMAL_OPERATION`, alongside a reminder that they are not certainties. Earlier model signals are labelled as early, with no probability presented as reliable. Backend confidence tiers come from the loaded artifact configuration; the profile view reads the same persisted attempt state rather than implementing its own threshold policy.

## Responsive design and accessibility

The neutral warm background, deep readable text, muted green accent, restrained borders, and system-font fallbacks define the visual system. Desktop uses a fixed sidebar. At 760px and below it switches to a compact header and five-destination bottom navigation; research remains secondary. Layout rules include a 320px minimum viewport, tablet breakpoint, and reduced-motion support.

Forms use labels, questions use fieldsets and radio controls, navigation is labelled, feedback uses a status region, and controls retain visible keyboard focus. Responsive CSS is included in the UI test suite; browser-based visual checks should still be run on supported devices before release.

## Development and validation

Run the backend from `backend/` with `python -m uvicorn app.main:app --reload`. Run the frontend from `frontend/` using `npm run dev`. To point at another backend, set `VITE_API_URL` in a local `.env` file.

- `npm test` runs the React Testing Library/Vitest suite with one worker (needed for the Windows development environment).
- `npm run build` type-checks and creates a production build.
- `python -m pytest -q -p no:cacheprovider` from repository root runs backend and ML tests.

The browser flow is in `scripts/browser_ui_e2e.mjs`. With backend on port 8000, Vite on port 5173, and Edge/Chrome exposing DevTools on port 9222, it enters a development profile, submits a live question, checks progress and mistake pages, and checks horizontal overflow at 320, 390, 768, 1024, and 1440 pixels. It appends test records to the configured development SQLite database. The automated frontend suite checks key empty/loading/error states and responsive CSS rules; it is not a substitute for manual browser/screen-reader review.
