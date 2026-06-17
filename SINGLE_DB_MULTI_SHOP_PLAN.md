# Single PostgreSQL Database Multi-Shop Plan

## Scope

This document is a design and migration plan only. It does not implement the
architecture change.

Goal: move from separate database-per-shop tenancy to one PostgreSQL database
with shop-level isolation for Adarsh Optical Group.

## Current Architecture Summary

The backend currently resolves a shop code from request context, then uses a
tenant database manager to open a database session for that shop. Several
repositories and services also carry `shop_key`/`shop_code` parameters and
filter data manually.

Important current touch points:

- `backend/app/db/session.py` resolves the current shop from headers, token
  claims, or host context.
- `backend/app/db/tenant.py` maps configured shop database URLs to SQLAlchemy
  engines/sessionmakers.
- `backend/app/core/shops.py` owns the canonical shop registry and legacy code
  aliases.
- Existing models often use `shop_key` strings for isolation, while some data
  is isolated only because it lives in a per-shop database.
- Existing scripts and background workers assume `tenant_db_manager` can open a
  session for a specific shop.

The new architecture should remove the separate per-shop database boundary and
make shop isolation explicit in schema, repository queries, service checks, and
tests.

## Target Decision

Use `shop_id` foreign keys on tenant-owned tables.

Keep `shops.code` as the stable public/canonical shop identifier used by API
requests, frontend route state, tokens, and logs.

Rationale:

- `shop_id` gives PostgreSQL referential integrity and compact indexes.
- `shops.code` can remain readable and stable at the API boundary.
- Legacy codes can resolve to one canonical shop row without copying legacy
  string values into every table.
- Shop display names, active state, locations, and future metadata can be
  changed in one table.
- It prevents orphaned rows that reference unknown shop strings.

## Shop Registry Tables

### `shops`

Canonical source of truth for business centers.

Suggested columns:

- `id`: bigint primary key
- `code`: text, unique, not null
- `display_name`: text, not null
- `location_label`: text, not null
- `center_type`: text, not null
- `is_active`: boolean, not null, default true
- `created_at`: timestamptz, not null
- `updated_at`: timestamptz, not null

Canonical rows:

- `adarsh-optical-centre`
- `adarsh-optometric-clinic`
- `adarsh-opticals-muxar`
- `adarsh-eye-boutique`

### `shop_aliases`

Recommended supporting table for legacy compatibility, even though it is not a
tenant-owned data table.

Suggested columns:

- `id`: bigint primary key
- `shop_id`: bigint foreign key to `shops.id`, not null
- `alias_code`: text, unique, not null
- `created_at`: timestamptz, not null

Initial aliases:

- `aadarsh-eye-boutique-center` -> `adarsh-eye-boutique`
- `adarsh-optometric-center` -> `adarsh-optometric-clinic`
- `adarsh-optical-center` -> `adarsh-optical-centre`

If a separate table feels too heavy for the first migration, the same mapping
can remain in `backend/app/core/shops.py` temporarily. The long-term preference
is a table so operational aliases can be managed without code deployment.

## Target Data Model

Tenant-owned tables should include `shop_id` directly. Even if a row also links
to another tenant-owned table, carrying `shop_id` keeps authorization checks,
indexes, audit logs, and cross-shop tests simple.

### `users`

Users are people/accounts, not shop records.

Suggested columns:

- `id`
- `email`, normalized lowercase
- `hashed_password`
- `full_name`
- `is_active`
- `last_login_at`
- `created_at`
- `updated_at`

Decision: keep staff/admin email globally unique in phase 1.

Reasoning:

- Current behavior appears to treat `users.email` as globally unique.
- Login and refresh-token behavior is simpler and safer.
- Multi-shop access is still possible through `user_shop_memberships`.
- If the business later requires the same email to represent different people in
  different shops, this can be revisited as a product decision.

### `user_shop_memberships`

Represents which shops a user can access.

Suggested columns:

- `id`
- `user_id`: foreign key to `users.id`
- `shop_id`: foreign key to `shops.id`
- `role`: admin/staff/owner/etc.
- `is_primary`: boolean
- `is_active`: boolean
- `created_at`
- `updated_at`

This replaces the current pattern of storing a single `shop_key` directly on
`users`. During migration, `users.shop_key` may remain temporarily for
compatibility, but new authorization should use memberships.

### `customers`

Suggested columns:

- `id`
- `shop_id`: foreign key to `shops.id`
- `customer_id`: business/customer code visible to staff
- customer profile fields
- contact fields
- `is_deleted`
- `created_at`
- `updated_at`

Rule: `customer_id` is unique per shop, not globally.

### `prescriptions`

Suggested columns:

- `id`
- `shop_id`: foreign key to `shops.id`
- `customer_id`: foreign key to `customers.id`
- prescription fields
- internal PDF file path fields
- public/signed URL metadata if needed
- `is_deleted`
- `created_at`
- `updated_at`

Access must require authenticated membership in the same `shop_id`.

### `bills`

Suggested columns:

- `id`
- `shop_id`: foreign key to `shops.id`
- `customer_id`: foreign key to `customers.id`
- `bill_number`
- status/tax/discount/total fields
- internal PDF file path fields
- `is_deleted`
- `created_at`
- `updated_at`

Rule: `bill_number` is unique per shop, not globally.

### `bill_items`

Target normalized table for bill line items.

Suggested columns:

- `id`
- `shop_id`: foreign key to `shops.id`
- `bill_id`: foreign key to `bills.id`
- item type/name/details
- quantity
- unit price
- discount/tax/line total fields
- `created_at`
- `updated_at`

If current bills store product/item details inline, migrate each existing bill
to one or more bill item rows. This can be done in a second phase after the
single database cutover if minimizing risk is more important than normalization.

### `payments`

Target normalized table for bill payments.

Suggested columns:

- `id`
- `shop_id`: foreign key to `shops.id`
- `bill_id`: foreign key to `bills.id`
- amount
- payment mode
- payment reference
- status
- paid at
- `created_at`
- `updated_at`

If current payment data is inline on bills, migrate paid amounts to one payment
row per bill where applicable.

### `vendors`

Suggested columns:

- `id`
- `shop_id`: foreign key to `shops.id`
- vendor profile/contact fields
- `is_active`
- `created_at`
- `updated_at`

Vendor uniqueness should be per shop unless the business explicitly wants a
group-wide vendor master.

### `campaigns`

Suggested columns:

- `id`
- `shop_id`: foreign key to `shops.id`
- campaign metadata
- target/filter fields
- status/schedule fields
- `created_at`
- `updated_at`

### `campaign_logs`

Suggested columns:

- `id`
- `shop_id`: foreign key to `shops.id`
- `campaign_id`: foreign key to `campaigns.id`
- customer/message delivery fields
- status/error fields
- `created_at`

### `whatsapp_logs`

Suggested columns:

- `id`
- `shop_id`: foreign key to `shops.id`
- related customer/bill/prescription/campaign references where applicable
- message metadata
- delivery status/error fields
- `created_at`

### `audit_logs`

Suggested columns:

- `id`
- `shop_id`: nullable foreign key to `shops.id`
- `user_id`: nullable foreign key to `users.id`
- action
- actor metadata
- target metadata
- request metadata
- `created_at`

`shop_id` should be nullable only for truly global events, such as failed
pre-shop authentication or system startup events.

### `chat_messages`

Decision: keep shop-isolated chat unless the product intentionally creates a
group-wide chat feature later.

Suggested columns:

- `id`
- `shop_id`: foreign key to `shops.id`
- `sender_user_id`: nullable foreign key to `users.id`
- message text
- internal attachment path
- attachment metadata
- `created_at`

Uploaded chat files should be stored in per-shop paths and downloaded only after
checking authenticated membership in the same shop.

### Supporting Tables

Existing auth/session tables such as refresh tokens should be reviewed even if
they are not tenant-owned business tables.

Recommended refresh token columns:

- `id`
- `user_id`
- `shop_id`
- token hash
- revoked/replaced metadata
- expires at
- created at

Including `shop_id` makes logout, rotation, audit logs, and shop mismatch checks
straightforward.

## Indexes And Constraints

### Shop Registry

- `shops.code`: unique
- `shops.is_active`: index
- `shop_aliases.alias_code`: unique
- `shop_aliases.shop_id`: index

### Users And Memberships

- `users.email`: unique on normalized lowercase email
- `users.is_active`: index
- `user_shop_memberships(user_id, shop_id)`: unique
- `user_shop_memberships(shop_id, role)`: index
- `user_shop_memberships(shop_id, is_active)`: index

### Customers

- `customers(shop_id, customer_id)`: unique
- `customers(shop_id, is_deleted, created_at)`: index
- `customers(shop_id, name)`: index if search uses name
- `customers(shop_id, mobile_number)`: index if search uses mobile
- `customers(shop_id, email)`: index if search uses email

### Prescriptions

- `prescriptions(shop_id, customer_id, created_at)`: index
- `prescriptions(shop_id, is_deleted, created_at)`: index
- Optional: `prescriptions(shop_id, prescription_number)`: unique if a visible
  prescription number exists

### Bills And Payments

- `bills(shop_id, bill_number)`: unique
- `bills(shop_id, customer_id, created_at)`: index
- `bills(shop_id, payment_status)`: index
- `bills(shop_id, is_deleted, created_at)`: index
- `bill_items(bill_id)`: index
- `bill_items(shop_id, bill_id)`: index
- `payments(bill_id)`: index
- `payments(shop_id, bill_id)`: index
- `payments(shop_id, paid_at)`: index

### Vendors

- `vendors(shop_id, is_active)`: index
- `vendors(shop_id, name)`: index
- Optional: `vendors(shop_id, normalized_name)`: unique if duplicates should be
  blocked per shop

### Campaigns And Logs

- `campaigns(shop_id, status, scheduled_at)`: index
- `campaign_logs(shop_id, campaign_id, created_at)`: index
- `campaign_logs(shop_id, status, created_at)`: index
- `whatsapp_logs(shop_id, created_at)`: index
- `whatsapp_logs(shop_id, status, created_at)`: index

### Audit Logs

- `audit_logs(shop_id, created_at)`: index
- `audit_logs(user_id, created_at)`: index
- `audit_logs(action, created_at)`: index

### Chat

- `chat_messages(shop_id, created_at)`: index
- `chat_messages(shop_id, id)`: index for attachment/download lookups

## Isolation Rules

1. Resolve request shop code through the canonical shop registry.
2. Convert the code to a `ShopContext` containing at least `shop_id`,
   `shop_code`, display name, and active state.
3. Authenticate the user.
4. Verify the user has an active membership for the requested `shop_id`.
5. Pass `shop_id` into repositories and services.
6. Every tenant-owned query must filter by `shop_id`.
7. Every download endpoint must check the record's `shop_id` before serving a
   file.
8. Background jobs must run with an explicit `shop_id`.

PostgreSQL Row Level Security can be considered after the app-level migration is
complete. It should not be the first line of defense until the application query
paths are consistently scoped and tested.

## Files Expected To Change During Implementation

Do not change these files as part of this design-only task. They are listed so
the implementation can be planned deliberately.

### Database And Configuration

- `backend/app/db/session.py`
- `backend/app/db/tenant.py`
- `backend/app/db/init_db.py`
- `backend/app/db/base.py`
- `backend/app/core/config.py`
- `backend/app/core/shops.py`
- `backend/.env.example`
- `.env.example`
- `README.md`

`tenant.py` should eventually be removed or reduced to a compatibility shim.
The app should use one SQLAlchemy engine/session factory from a PostgreSQL
`DATABASE_URL`.

### Models

- Add `backend/app/models/shop.py`
- Add `backend/app/models/user_shop_membership.py`
- Update `backend/app/models/user.py`
- Update `backend/app/models/customer.py`
- Update `backend/app/models/prescription.py`
- Update `backend/app/models/bill.py`
- Add or update `backend/app/models/bill_item.py`
- Add or update `backend/app/models/payment.py`
- Update `backend/app/models/vendor.py`
- Update `backend/app/models/campaign.py`
- Update `backend/app/models/chat.py`
- Update `backend/app/models/whatsapp_log.py`
- Update `backend/app/models/audit_log.py`
- Update refresh token/session models if present

### Repositories

- `backend/app/repositories/user_repository.py`
- `backend/app/repositories/customer_repository.py`
- `backend/app/repositories/prescription_repository.py`
- `backend/app/repositories/bill_repository.py`
- `backend/app/repositories/vendor_repository.py`
- `backend/app/repositories/campaign_repository.py`
- `backend/app/repositories/chat_repository.py`
- Repositories for campaign logs, WhatsApp logs, audit logs, and auth tokens

Repository methods should accept `shop_id` or a `ShopContext`, not unvalidated
shop strings.

### Services

- `backend/app/services/auth_service.py`
- `backend/app/services/customer_service.py`
- `backend/app/services/prescription_service.py`
- `backend/app/services/bill_service.py`
- `backend/app/services/vendor_service.py`
- `backend/app/services/campaign_service.py`
- `backend/app/services/chat_service.py`
- `backend/app/services/analytics_service.py`
- `backend/app/services/staff_service.py`
- `backend/app/services/shop_identity_service.py`
- PDF generation and document delivery services
- WhatsApp/email/logging services

### Endpoints And Dependencies

- `backend/app/api/deps.py`
- Auth endpoints
- Customer endpoints
- Prescription endpoints
- Bill endpoints
- Vendor endpoints
- Campaign endpoints
- Staff endpoints
- Analytics endpoints
- Chat endpoints
- Public shop resolver endpoints
- Document download endpoints

Endpoint dependencies should expose `current_shop`/`ShopContext`, not just a
raw shop key.

### Migrations And Scripts

- New Alembic migration creating `shops`, `shop_aliases`, and memberships
- Migration adding `shop_id` to tenant-owned tables
- Migration/backfill scripts for importing separate shop databases
- `backend/scripts/migrate_all_shops.py`
- `backend/scripts/init_dev_db.py`
- `backend/scripts/seed.py`
- `backend/scripts/manual_qa_smoke.py`
- Background workers such as campaign senders

### Tests

- Auth tests
- Shop resolver tests
- Membership authorization tests
- Customer CRUD tests
- Bill CRUD tests
- Prescription/document permission tests
- Chat visibility/download tests
- Campaign/WhatsApp log tests
- Migration dry-run tests
- Cross-shop negative tests for every sensitive resource

## Migration Strategy

### Phase 0: Freeze, Inventory, And Backups

1. Identify every current shop database URL and map it to a canonical
   `shops.code`.
2. Take verified backups of every source database.
3. Put source databases in a known state before final cutover, ideally through a
   maintenance window.
4. Inventory generated files and confirm their source shop.
5. Record row counts for every table in every source database.
6. Record max IDs and any business identifiers such as customer IDs and bill
   numbers.

Rollback remains easy in this phase because no source database is modified.

### Phase 1: Build The New PostgreSQL Schema

1. Create the single PostgreSQL database.
2. Run migrations for `shops`, optional `shop_aliases`, `users`,
   `user_shop_memberships`, and tenant-owned tables with `shop_id`.
3. Seed the four canonical shops.
4. Seed legacy aliases.
5. Keep old per-shop databases untouched.

### Phase 2: Import Data Shop By Shop

Use an explicit ETL/import script rather than relying only on Alembic schema
migrations.

For each source shop:

1. Resolve the source database to a canonical `shop_id`.
2. Insert tenant-owned rows with that `shop_id`.
3. Build migration mapping tables or files:
   - source shop code
   - source table
   - old primary key
   - new primary key
4. Use mapping data to update foreign keys, especially for customers, bills,
   prescriptions, logs, and files.
5. Keep document file paths internal and include shop-specific path prefixes.

Do not assume old integer IDs are globally unique across shop databases.

### Phase 3: Users And Memberships

1. Normalize all emails before import.
2. Merge users by normalized email if they represent the same person.
3. Create one `user_shop_memberships` row per imported user/shop relationship.
4. Preserve roles from the source databases.
5. For duplicate emails with conflicting passwords or identities, block the
   migration until reviewed, or create a manual merge report.

Phase 1 product decision: user email is globally unique. That means duplicate
email conflicts must be resolved during migration instead of creating multiple
users with the same email.

### Phase 4: Compatibility Cutover In Code

1. Replace `tenant_db_manager` usage with one global SQLAlchemy session.
2. Replace raw shop string dependencies with `ShopContext`.
3. Update auth to issue tokens containing canonical `shop_code` and/or
   `shop_id`.
4. Verify token shop claims against active memberships.
5. Update repositories one resource at a time so every query filters by
   `shop_id`.
6. Update workers and scripts to use explicit `shop_id`.
7. Keep legacy shop aliases resolving to canonical shop rows.

During this phase, temporary columns such as legacy `shop_key` may remain for
comparison and rollback. They should be removed only after successful production
cutover and validation.

### Phase 5: Validation

Before production cutover:

1. Compare source and target row counts by shop and table.
2. Check foreign key integrity.
3. Check uniqueness constraints:
   - customer business ID per shop
   - bill number per shop
   - email globally
4. Run cross-shop access tests for customers, bills, prescriptions, PDFs, chat,
   and logs.
5. Run document download tests for each shop.
6. Run auth login, refresh, logout, and membership tests.
7. Run analytics/reporting smoke tests per shop.
8. Run background campaign/WhatsApp dry-run tests.

### Phase 6: Production Cutover

1. Put the app into maintenance mode.
2. Take final source database backups.
3. Run the final import.
4. Run validation checks.
5. Update environment variables to the new PostgreSQL `DATABASE_URL`.
6. Deploy the single-db application.
7. Monitor auth, billing, PDF downloads, chat, campaign jobs, and error logs.
8. Keep old databases read-only until the new system has passed an agreed
   observation period.

## Rollback Plan

The safest rollback is to keep the original per-shop databases unchanged during
migration.

If cutover fails before writes occur in the new system:

1. Revert the application deployment to the previous per-shop DB version.
2. Restore environment variables using the previous `SHOP_DATABASES` settings.
3. Point traffic back to the old application/database setup.

If cutover fails after writes occur in the new system:

1. Stop traffic or re-enter maintenance mode.
2. Decide whether new writes can be discarded, replayed, or manually reconciled.
3. Use audit logs and migration mapping data to identify post-cutover changes.
4. Restore the old deployment only after deciding how to handle those writes.
5. Keep the single PostgreSQL database snapshot for investigation.

Because post-cutover rollback with live writes is risky, the first production
cutover should happen inside a maintenance window with a clear go/no-go point
after validation and before staff resume normal use.

## Risks And Mitigations

### Missed Shop Filter

Risk: a repository or endpoint could return another shop's data.

Mitigation:

- Require `shop_id` in repository method signatures for tenant-owned data.
- Add cross-shop negative tests for each resource.
- Consider a code review checklist item: every tenant-owned query must filter by
  `shop_id`.
- Consider PostgreSQL Row Level Security after the application migration is
  stable.

### ID Collisions

Risk: separate shop databases may contain the same integer primary keys.

Mitigation:

- Do not preserve old IDs blindly.
- Use migration mapping tables/files from old IDs to new IDs.
- Validate all foreign keys after import.

### Business Identifier Collisions

Risk: customer IDs and bill numbers may collide globally.

Mitigation:

- Make uniqueness per shop, not global.
- Validate `customers(shop_id, customer_id)` and `bills(shop_id, bill_number)`.

### Duplicate User Emails

Risk: the same email may exist in multiple shop databases with different
passwords or identities.

Mitigation:

- Normalize emails before import.
- Keep global unique email in phase 1.
- Generate a manual conflict report before final cutover.
- Create memberships only after identity conflicts are resolved.

### Background Worker Leakage

Risk: workers may run without a shop context after the tenant manager is
removed.

Mitigation:

- Make worker jobs carry explicit `shop_id`.
- Add worker tests or dry-run scripts per shop.
- Log `shop_id` in job audit records.

### Document Path Leakage

Risk: PDFs or chat attachments may be served from old public/static paths.

Mitigation:

- Store internal file paths only.
- Require authenticated download endpoints.
- Put files under per-shop directories.
- Test cross-shop download denial.

### Performance Regressions

Risk: tables that were small per shop become larger shared tables.

Mitigation:

- Add composite indexes beginning with `shop_id`.
- Validate query plans for customer search, bill search, analytics, chat, and
  logs.
- Add pagination where missing.

### Legacy Alias Confusion

Risk: old shop codes in tokens, URLs, or stored data may stop working.

Mitigation:

- Resolve legacy aliases to canonical `shops.code`.
- Keep aliases during migration.
- Issue new tokens with canonical codes after login/refresh.
- Remove aliases only after logs show they are no longer used.

## Recommended Implementation Order

1. Add the new schema plan to migrations in a branch, including shops,
   memberships, and `shop_id` columns.
2. Add a `ShopContext` dependency while keeping the old shop key interface
   available as a compatibility layer.
3. Update auth and membership checks.
4. Update repositories/services by vertical slice:
   - customers
   - bills and payments
   - prescriptions and documents
   - vendors
   - campaigns and WhatsApp logs
   - chat
   - analytics
5. Update scripts and workers.
6. Build import tooling and run repeated dry runs against database copies.
7. Add and pass cross-shop isolation tests.
8. Deploy to staging with production-like data.
9. Cut over production during a maintenance window.
10. Remove temporary `shop_key` compatibility only after stable production use.

## Completion Criteria For The Future Implementation

- The app uses one PostgreSQL `DATABASE_URL`.
- `tenant_db_manager` is removed or no longer opens per-shop databases.
- Every tenant-owned table has `shop_id`.
- Every tenant-owned repository query filters by `shop_id`.
- Users access shops through memberships.
- Legacy shop codes resolve to canonical shop rows.
- Customer business IDs are unique per shop.
- Bill numbers are unique per shop.
- Staff/admin emails are globally unique unless the product decision changes.
- Cross-shop access tests pass for data and documents.
- Old per-shop databases are backed up and retained read-only through the
  agreed observation period.
