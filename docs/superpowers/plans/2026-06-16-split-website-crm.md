# Website And CRM Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the current combined React frontend into two independent Vite apps: `website/` for the public Adarsh Optical Group website and `crm/` for the CRM.

**Architecture:** `crm/` is copied from the current frontend and retains all CRM features, auth, API clients, styles, and tests, but removes public website routes/components. `website/` is a smaller app containing only the current public website UI and its own routing, dependencies, Tailwind config, tests, and build commands. `backend/` remains unchanged.

**Tech Stack:** React 18, Vite, TypeScript, Tailwind CSS, React Router, Vitest, ESLint.

---

### Task 1: Create Separate App Folders

**Files:**
- Create: `crm/`
- Create: `website/`
- Read: `frontend/`

- [ ] Copy the current `frontend/` app into `crm/`, excluding generated and local-only artifacts: `node_modules`, `dist`, `.env`, `*.tsbuildinfo`.
- [ ] Copy only the required Vite/Tailwind/TypeScript scaffolding into `website/`.
- [ ] Keep `backend/` untouched.

### Task 2: Make CRM Independent

**Files:**
- Modify: `crm/src/app/router.tsx`
- Modify: `crm/src/lib/routes.ts`
- Delete from CRM: `crm/src/pages/public/`, `crm/src/components/public/`
- Modify: `crm/index.html`
- Modify: `crm/package.json`

- [ ] Remove public website routes (`/`, `/about`, `/centers`, `/collections`, `/contact`) from the CRM router.
- [ ] Make `/` redirect to `/crm` or render the CRM launch page.
- [ ] Keep all CRM routes under `/crm/...`.
- [ ] Keep the current CRM visual style and landing/access UI.
- [ ] Rename package metadata to identify this as the CRM app.

### Task 3: Make Website Independent

**Files:**
- Create/modify: `website/src/main.tsx`
- Create/modify: `website/src/App.tsx`
- Create/modify: `website/src/pages/HomePage.tsx`
- Create/modify: `website/src/components/PublicHeader.tsx`
- Create/modify: `website/src/components/PublicFooter.tsx`
- Create/modify: `website/src/index.css`
- Modify: `website/package.json`
- Modify: `website/vite.config.ts`

- [ ] Preserve the current public homepage UI and styling.
- [ ] Keep public routes only: `/`, `/about`, `/centers`, `/collections`, `/contact`.
- [ ] Keep CRM links pointed to `/crm` by default so deployment can later route them to the CRM host/subdomain.
- [ ] Remove CRM-only dependencies and files from the website app.

### Task 4: Update Documentation

**Files:**
- Modify: `README.md`
- Create/modify: `crm/.env.example`
- Create/modify: `website/.env.example`

- [ ] Document separate dev commands for backend, CRM, and website.
- [ ] Document that `frontend/` is legacy combined code if left in place temporarily.
- [ ] Keep real `.env` files out of source control.

### Task 5: Verify

**Commands:**
- [ ] `cd crm && npm install` if dependencies are not present, then `npm run typecheck`, `npm run lint`, `npm test -- --run`, `npm run build`.
- [ ] `cd website && npm install` if dependencies are not present, then `npm run typecheck`, `npm run lint`, `npm test -- --run`, `npm run build`.
- [ ] Confirm backend still compiles with `cd backend && venv/bin/python -m compileall app`.
