# Adarsh CRM Replacement Phase 10 Design

## Scope

Phase 10 adds auditable operational completion, delivery, delay handling, generalized follow-ups, and a chronological patient workflow timeline. It builds on the completed visit, prescription, spectacle order, contact-lens order, billing, audit, WhatsApp, email, and campaign modules.

This phase does not introduce inventory, a new messaging platform, a generic project-management system, or unrelated clinical workflows. Existing order, billing, prescription, and communication services remain authoritative for their current responsibilities.

## Considered Approaches

1. **Append-only workflow events with current status fields:** Selected. Current entity fields remain efficient for operational screens, while immutable events provide complete history and patient-timeline records.
2. **Audit logs only:** Rejected because audit payloads are implementation-oriented, awkward to query as patient history, and do not provide a stable operational event contract.
3. **JSON history arrays on each entity:** Rejected because concurrent updates, filtering, reporting, and cross-entity timelines would be fragile and duplicated.

## Workflow Event Model

Migration `0014_order_completion_delivery_followup` creates a branch-scoped `workflow_events` table. Each event stores:

- patient and visit references;
- event type;
- related entity type and identifier;
- occurred date and time;
- actor user;
- optional notes;
- optional previous and new status;
- small structured metadata for references such as prescription version, bill number, payment amount, or expected ready date;
- creation timestamp.

Events are append-only. Services may create events but do not update or delete prior events. Existing `audit_logs` remain unchanged and continue to serve technical auditing. Workflow events are the stable patient-facing operational history.

Phase 10 records these milestones where applicable:

- prescription finalized;
- prescription card generated;
- prescription amendment created and finalized;
- invoice created and generated;
- spectacle ordered;
- contact lens ordered;
- vendor order sent;
- order in production;
- order ready for delivery;
- order delivered;
- order delayed and delay cleared;
- follow-up scheduled, completed, or cancelled;
- order cancelled.

Events are written in the same transaction as the related state change whenever both use the database transaction. PDF generation stores its event after the file reference is persisted successfully. Failed actions do not create success events.

## Order Status and Delivery

The existing order status vocabulary remains:

`draft -> ready_for_vendor -> sent_to_vendor -> in_production -> ready_for_delivery -> delivered`

Cancellation remains available only from non-terminal states. Delivered and cancelled are terminal. Existing controlled-transition maps remain the source of truth and are extended only to record notes and workflow events.

Both spectacle and contact-lens orders gain nullable `delivered_by` and `delivered_at` fields. Only an order currently in `ready_for_delivery` can be marked delivered. Delivery records the authenticated user and server time in the same transaction as the status and event. Repeated delivery requests return the existing delivered state without creating duplicate delivery events; attempts from any other state return a conflict.

Delay is an operational marker, not a lifecycle status. Both order types gain nullable `is_delayed`, `delay_reason`, `expected_ready_date`, `delay_marked_by`, and `delay_marked_at` fields. A non-terminal order can be marked delayed with a required reason and optional expected date. Clearing a delay preserves both delay and clear events. Delivered or cancelled orders cannot be newly delayed. UI badges show delayed and cancelled states clearly without inventing contradictory transitions.

Order status requests accept optional notes. Status events store the prior status, new status, actor, server timestamp, and notes. Existing vendor WhatsApp sending remains authoritative for the spectacle `sent_to_vendor` milestone.

## Generalized Follow-Ups

The existing branch-scoped `follow_up_tasks` table is generalized rather than replaced. Migration `0014` makes the contact-lens-order link optional, adds an optional spectacle-order link, removes the one-task-per-contact-lens-order restriction, and adds:

- follow-up type;
- assigned staff user;
- reminder state;
- completion notes;
- existing due date, status, notes, completion actor/time, visit, patient, and user tracking.

Supported types are:

- contact lens;
- progressive adaptation;
- pediatric review;
- referral follow-up;
- dry-eye review;
- custom follow-up.

Every task belongs to a patient and visit. Order links are optional and validated against the same patient, visit, and branch. Assigned staff must be active in the current branch. Pending tasks may change due date, assignment, notes, and reminder state. Only pending tasks can become completed or cancelled. Completion requires optional completion notes and records the actor and server time. Terminal tasks remain read-only and visible in history.

The current contact-lens scheduling API continues to work by finding or updating the pending contact-lens task for that visit and order. New visit-scoped follow-up endpoints list, create, update, complete, and cancel general follow-ups.

No new reminder transport is introduced. Existing invoice email/WhatsApp, vendor WhatsApp, and campaigns remain the available communication tools. The follow-up workspace records reminder state and links staff to the existing Campaigns area when communication is needed.

## Patient Timeline

Customer detail adds a chronological timeline generated from stable persisted records. It includes:

- visits;
- finalized visit prescriptions and amendments;
- referrals;
- spectacle and contact-lens orders;
- bills and invoice generation;
- payments;
- workflow status, delay, delivery, and follow-up events.

The service produces a common timeline contract with event type, title, timestamp, status, notes, actor, visit, entity reference, and safe metadata. Records are scoped through the current branch before aggregation. Clinical payloads, private document paths, and unrelated audit metadata are not exposed.

Existing patient detail sections remain available. The CRM adds a unified Timeline section ordered newest first, with links back to the related visit or bill where available. Empty and loading states follow the current Patient Records page.

## CRM Workspaces

The existing visit sidebar and page shell remain unchanged.

- Spectacle and contact-lens order workspaces show current status, delayed/cancelled badges, delivery actor/time, a compact event history, and an optional note field for status actions.
- Only the valid next status action is offered. Delivery uses an explicit confirmation and cannot appear before `ready_for_delivery`.
- Delay and clear-delay controls are inline and do not use a separate order screen.
- The existing `Completion and Follow-Up` section becomes a focused follow-up workspace for the visit. It lists historical tasks and allows creation, pending-task edits, completion, and cancellation.
- Patient Records gains the unified chronological timeline while preserving the existing visits, referrals, prescriptions, contact-lens orders, follow-ups, and bills summaries.

Unsaved notes or follow-up form changes participate in the current visit workspace navigation warning. Mutations show saving, success, and persistent error states without discarding entered values.

## Isolation and Validation

Every workflow-event, order, follow-up, staff, visit, patient, and bill lookup is scoped through the authenticated shop. Cross-shop identifiers return not found rather than exposing another branch's existence.

Validation rules include:

- delivery only from `ready_for_delivery`;
- no transition out of delivered or cancelled;
- no delay on terminal orders;
- required reason when marking delayed;
- follow-up due date cannot be in the past;
- assigned staff must be active in the current branch;
- linked order, visit, and patient must match;
- terminal follow-ups cannot be edited or reopened;
- event rows cannot be edited or deleted through the API.

Database or concurrent-update conflicts return clear conflict errors. A failed event insert rolls back its related state mutation so operational state and history cannot diverge.

## Compatibility

- Existing visits, prescriptions, orders, bills, payments, audit logs, and communication records remain valid.
- New order fields are nullable or defaulted.
- Existing contact-lens follow-up rows migrate without loss.
- Existing order status endpoints remain compatible because status notes are optional.
- Current financial calculations, invoice generation, prescription PDFs, and communication delivery are not duplicated.

## Testing

Backend tests cover:

- append-only event creation for every required milestone;
- previous/new status, actor, timestamp, and notes;
- spectacle and contact-lens transition rules;
- delivery actor/time and idempotency;
- delay marking, clearing, and terminal restrictions;
- all follow-up types, assignment, reminder state, completion notes, and terminal behavior;
- legacy contact-lens follow-up compatibility;
- patient timeline aggregation and ordering;
- cross-shop isolation;
- clean migration from revision `0013` to `0014`.

CRM tests cover:

- status history and notes;
- delivery controls and confirmation;
- delayed and cancelled presentation;
- generalized follow-up creation and completion;
- persistent mutation errors and unsaved-change warnings;
- complete patient timeline rendering and navigation;
- continued use of existing billing and communication links.

Full backend and CRM verification runs after focused tests. Phase 10 stops after these workflows and does not begin a later phase.
