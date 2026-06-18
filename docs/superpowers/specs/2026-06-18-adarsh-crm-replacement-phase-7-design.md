# Adarsh CRM Replacement Phase 7 Design

## Scope

Phase 7 adds spectacle dispensing and lens ordering to the active `crm/` visit workspace. It does not add inventory, contact-lens, billing, or new clinical examination behavior.

## Verified Reuse

- `Visit`, `VisitPrescription`, and the versioned final-prescription service remain the clinical source of truth.
- `VendorRepository` remains the shop-scoped vendor source.
- `WhatsAppService` remains the only provider integration and delivery log writer.
- `AuditService` records order creation, updates, prescription relinking, document generation, status changes, and vendor sending.
- `document_file_service` and private media directories remain the file-reference boundary.
- No inventory/product module currently exists. Frame details are therefore stored as an order snapshot, without introducing duplicate stock logic.

## Data Model

Add one shop-scoped `DispensingOrder` per visit. The order stores:

- visit, customer, exact finalized prescription version, optional vendor, and branch scope;
- stable order reference and lifecycle status;
- structured frame, measurement, and lens snapshots;
- manufacturing instructions, separate from clinical notes;
- private vendor-document path;
- creator/updater and vendor-send audit fields.

The linked prescription never changes silently. The API reports when the linked version is no longer current. A draft or ready order can be explicitly relinked to the current finalized version; already-sent orders retain their historical version.

## API Boundary

- `GET /visits/{visit_id}/dispensing-order` returns current prescription context and the optional order.
- `PUT /visits/{visit_id}/dispensing-order` creates or updates an incomplete draft safely.
- `POST /visits/{visit_id}/dispensing-order/relink-current` explicitly changes a draft/ready order to the current finalized version.
- `POST /visits/{visit_id}/dispensing-order/status` applies controlled lifecycle transitions.
- `POST /visits/{visit_id}/dispensing-order/vendor-document` generates the private vendor PDF.
- `GET /visits/{visit_id}/dispensing-order/vendor-document/download` performs authenticated, shop-scoped download.
- `POST /visits/{visit_id}/dispensing-order/send-vendor` generates the vendor document, sends it through the existing WhatsApp service, and records the result.

All repository reads include shop scope. Cross-shop visits, prescriptions, vendors, orders, and documents return not found or invalid-shop errors.

## Validation and Lifecycle

Drafts may be incomplete. Numeric values are validated only when supplied. Vendor sending requires:

- a current finalized linked prescription;
- an active shop-owned vendor;
- a lens type;
- explicit ready-for-vendor status.

Statuses are `draft`, `ready_for_vendor`, `sent_to_vendor`, `in_production`, `ready_for_delivery`, `delivered`, and `cancelled`. Invalid backward or terminal transitions are rejected.

## Vendor Document Privacy

The vendor PDF includes order reference, branch, linked prescription version and powers, frame snapshot, dispensing measurements, lens specification, and manufacturing instructions. It excludes patient mobile/address, visit reason, referrals, torch/slit-lamp findings, and private clinical notes. It is stored privately and downloaded only through authenticated shop-scoped routes.

## CRM Experience

The existing `Frame and Dispensing` and `Lens Order` navigation entries open a shared order workspace. The page shows the fixed prescription version, current/stale state, order status, unit-labelled measurements, vendor selection, independent save feedback, private PDF actions, and WhatsApp sending. Existing generic section storage is not deleted, preserving prior draft payloads for compatibility.

## Compatibility

- Existing patient, visit, prescription, vendor, WhatsApp, billing, and legacy prescription flows remain available.
- Existing `frame_dispensing` and `lens_order` exam-section rows are retained but new saves use the dedicated order aggregate.
- No historical prescription or PDF is modified.
- The migration is additive and reversible by dropping only the new table and status enum. The WhatsApp enum value is harmless if retained after downgrade on PostgreSQL.

