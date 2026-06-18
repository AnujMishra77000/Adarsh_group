# Adarsh CRM Replacement Phase 6 Design

## Scope

Phase 6 adds encounter-based final prescriptions and visit completion to the active `crm/` application. It does not replace or mutate the legacy `prescriptions` table, legacy prescription pages, vendor sending, billing, or historical PDFs.

## Architecture

Add a `visit_prescriptions` table linked to `visits`, `customers`, `shops`, and users. Each row is one immutable-capable prescription version. A visit may have one editable draft and any number of finalized, superseded, or cancelled historical versions. A unique `(visit_id, version_number)` constraint preserves ordering, while service-level transactions ensure only one current finalized version.

The existing `visit_exam_sections.final_prescription` record remains a workspace progress marker and compatibility snapshot. The version service is the authority for final prescription drafting and finalization. Once a current prescription is finalized, generic section saving for `final_prescription` is rejected; corrections begin through the amendment endpoint.

## Prescription Data

Each version stores:

- distance values for right and left eye: sphere, cylinder, axis, visual acuity;
- near values for right and left eye: sphere, cylinder, axis, add, visual acuity;
- clinically relevant PD and fitting values;
- patient instructions;
- version number, status, current flag, amendment parent, finalized user/time;
- an internal PDF file reference for that exact finalized version.

Clinical values use JSON snapshots because the existing examination workspace already stores section payloads as JSON and Phase 6 needs an immutable versioned snapshot. Vendor costing, order details, and internal advanced-examination notes are excluded.

## Workflow

1. Opening Final Prescription loads the version history and creates version 1 draft only when the user first saves.
2. Draft saves validate optical formats leniently enough to preserve incomplete work.
3. Review combines patient/visit/examiner context, completed core section summaries, final prescription values, referral summary, instructions, and explicit warnings.
4. Finalization requires `confirmed=true`, performs strict optical validation, records actor/time, marks the version current, completes the final-prescription section, and emits an audit event.
5. Finalized versions are read-only. Starting an amendment copies the current finalized values into a new draft with the next version number.
6. Finalizing an amendment marks the previous current version superseded but retains its data and file reference.
7. Visit completion requires explicit confirmation and a current finalized prescription. It marks the visit completed and emits an audit event.

## PDF Rules

The patient PDF endpoint resolves only the current finalized version for a visit. The document includes patient identity, branch, prescription date, examiner, version identifier, distance/near values, PD/fitting values, and patient instructions. It excludes contact details, vendor costing, order notes, and internal clinical findings. A new amendment changes current-version resolution, so an older PDF is never returned or labelled as current.

## Compatibility And Isolation

Legacy prescriptions remain available through existing `/prescriptions` APIs and CRM pages without new validation. All encounter prescription repository lookups scope through the current shop and visit. Cross-shop reads, writes, finalization, amendment, completion, and PDF access return not found or forbidden consistently with existing visit services.

## Testing

Backend service tests cover draft editing, explicit finalization, immutability, amendment history/current selection, strict validation, audit fields, current-only PDF selection, completion, and cross-shop denial. CRM tests cover distance/near entry, structured review, confirmation, read-only finalized state, amendment creation, version history, warnings, and completion controls. Full compile, lint, typecheck, test, and build checks close the phase.
