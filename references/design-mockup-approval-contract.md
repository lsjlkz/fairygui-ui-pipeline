# Full-Screen Design Mockup And Approval Contract

## Purpose

Use this contract when a complete game UI screen is being created from requirements, UX/UI documents, gameplay notes, or a partial visual reference.

The pipeline must first generate a full-screen design mockup, obtain explicit human confirmation, and only then continue to semantic decomposition, layout extraction, production asset planning, FairyGUI assembly, or XML generation.

## Core Rule

A generated design mockup is a proposal, not an approved source of truth.

Do not continue past the design stage unless `reports/design_approval.json` exists and passes the executable approval gate.

The AI must never approve its own design. It may create or update a pending/rejected approval record, but it may set `status=approved` only after the user explicitly confirms the exact design file or an existing human approval record is supplied.

## When This Contract Is Mandatory

Mandatory for:

- building a complete game UI screen from requirements or design documents
- creating a new full-screen visual direction before asset production
- reconstructing a complete screen from partial references
- redesigning an existing complete screen
- generating a full-screen mockup that will become the source for layout and resource decomposition

Not mandatory for:

- XML-only validation or repair
- ID registry repair
- Unity binding generation
- replacing or redrawing one isolated asset
- projects that already provide a confirmed final design image and a valid approval record

## Required Input

Before mockup generation:

- `specs/ui_spec.md`
- at least one valid primary reference image
- target design resolution
- target screen and screen goal
- required functional regions
- component/state requirements
- text-baking policy
- forbidden visual elements

Create `specs/visual_design_brief.md` before calling image generation.

## visual_design_brief.md Required Sections

- Confirmed Requirement Sources
- Screen Goal
- Design Resolution
- Primary Reference And Allowed Uses
- Functional Region Map
- Required Components And States
- Visual Hierarchy
- Art Direction
- Text And Localization Policy
- Asset Separation Constraints
- Negative Constraints
- Mockup Acceptance Criteria
- Known Risks

## Mockup Output

Store full-screen design candidates under:

```text
UIProduction/generated/design/
├── screen_design_draft_v1.png
├── screen_design_draft_v2.png
└── screen_design_final.png
```

The exact names may differ, but the approved file must remain inside the current `UIProduction` directory.

A design mockup should show the complete screen composition, functional areas, visual hierarchy, perspective, lighting, color relationship, component scale, and interaction-space allocation.

Do not treat the mockup as production-ready sliced art. Dynamic objects, state variants, text, list items, and interaction feedback still require semantic analysis and production-safe assets.

## Approval Record

Use `reports/design_approval.json`. Create a pending record deterministically after generating a candidate:

```bash
python scripts/record_design_approval.py --root UIProduction --action pending --file generated/design/screen_design_draft_v1.png --note "Waiting for user confirmation"
```

After the user explicitly confirms the exact file, record approval and compute its real dimensions and SHA-256:

```bash
python scripts/record_design_approval.py --root UIProduction --action approve --file generated/design/screen_design_final.png --approved-for semantic_analysis layout_analysis asset_planning resource_generation fairygui_assembly xml_generation --confirmation-type user_confirmation --recorded-by user --note "User explicitly approved this exact file"
```

Do not run the `approve` action before explicit confirmation.

Use `reports/design_approval.json`:

```json
{
  "version": "0.1.0",
  "status": "pending",
  "candidateFile": "generated/design/screen_design_draft_v1.png",
  "approvedFile": null,
  "resolution": [1920, 1080],
  "approvedFor": [],
  "confirmation": null,
  "knownDeviations": [],
  "reviewNotes": [],
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

After explicit human confirmation, it may become:

```json
{
  "version": "0.1.0",
  "status": "approved",
  "candidateFile": "generated/design/screen_design_final.png",
  "approvedFile": "generated/design/screen_design_final.png",
  "approvedFileSha256": "<sha256-of-the-approved-image>",
  "resolution": [1920, 1080],
  "approvedFor": [
    "semantic_analysis",
    "layout_analysis",
    "asset_planning",
    "resource_generation",
    "fairygui_assembly",
    "xml_generation"
  ],
  "confirmation": {
    "type": "user_confirmation",
    "recordedBy": "user",
    "note": "The user explicitly approved this exact design file.",
    "confirmedAt": "2026-01-01T00:00:00Z"
  },
  "knownDeviations": [],
  "reviewNotes": [],
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

Allowed `status` values:

- `pending`
- `approved`
- `rejected`
- `superseded`

Allowed confirmation types for approval:

- `user_confirmation`
- `manual_review`

`ai_self_approval`, `automatic`, inferred approval, silence, or continuation requests that do not identify the approved design are invalid.

## Approval Scope

A design may be approved for one or more stages:

- `semantic_analysis`
- `layout_analysis`
- `asset_planning`
- `resource_generation`
- `fairygui_assembly`
- `xml_generation`

The requested next stage must appear in `approvedFor`.

Recommended default after the user approves the final full-screen design is to approve all downstream stages. If the user approves only visual direction but not exact layout, limit approval to the explicitly accepted scope.

## Hard Blocking Rules

The design approval gate fails when:

- `ui_spec.md` is missing
- `visual_design_brief.md` is missing or lacks required sections
- `design_approval.json` is missing or invalid
- status is not `approved`
- `approvedFile` is missing
- the approved file does not exist
- `approvedFileSha256` is missing or does not match the current file
- approved image pixels do not match `resolution`
- the requested stage is absent from `approvedFor`
- confirmation is missing or not human-originated
- the approved file is outside the current `UIProduction` tree
- the approval record points to a draft that was later superseded

When blocked, output `设计稿确认阻塞报告` and stop the requested downstream stage.

## Revisions

When the design changes after approval:

1. mark the old record `superseded`
2. set the new record to `pending`
3. regenerate or revise the mockup
4. request confirmation for the exact new file
5. rerun `scripts/check_design_approval.py`

Do not silently carry approval from an old image to a modified image. The SHA-256 value binds the approval to the exact image bytes.

## Downstream Source Rule

After approval:

- `uxui_semantic_spec.md` must name the approved design file as its visual source
- `layout_spec.json.sourceImages` must include the approved design file
- `slice_plan.json.sourceImages` must include the approved design file when it is used for crop analysis
- input snapshots must include the approved design image and approval record

The primary reference image remains an art/style source. The approved full-screen design becomes the screen composition and layout source.
