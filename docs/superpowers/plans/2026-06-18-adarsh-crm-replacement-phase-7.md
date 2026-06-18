# Phase 7 Implementation Plan

1. Add service-level tests for draft persistence, exact prescription-version linkage, stale detection/relinking, lifecycle rules, shop isolation, vendor document privacy, and WhatsApp sending.
2. Add `DispensingOrder`, lifecycle enums, Pydantic contracts, shop-scoped repository, Alembic migration, and model relationships.
3. Implement order orchestration, private vendor PDF generation/download, audit events, and existing vendor/WhatsApp integration.
4. Expose visit-scoped Phase 7 endpoints without changing legacy routes.
5. Add CRM API/types and failing workspace tests for frame fields, unit-labelled measurements, lens/vendor fields, save state, stale-version warning, status, PDF, and vendor send.
6. Replace only the two Phase 7 placeholder forms with a shared dispensing-order workspace.
7. Run backend compile, migration, lint, full tests, and CRM lint/typecheck/tests/build. Stop after Phase 7.
