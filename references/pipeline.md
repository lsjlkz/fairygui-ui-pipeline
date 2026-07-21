# FairyGUI UI Production Pipeline

## Purpose

This pipeline turns game UI requirements into FairyGUI-ready production artifacts. It is intentionally semi-automatic: documents and manifests are strict, while image generation, visual QA, and FairyGUI editor publishing require checkpoints.

Before applying this enhanced pipeline, read the complete embedded originals `references/fairygui-ai-generation-workflow.md` and, for XML work, `references/fairygui-xml-parsing-specification.md`. This file extends those originals with stricter gates; it does not replace, summarize, or permit skipping them.

This file is reusable skill guidance. Keep only generic workflow, gates, schemas, and validation rules here. Store concrete project data such as screen names, layout coordinates, crop boxes, package IDs, resource IDs, component IDs, and design-image analysis outputs in the active project's `UIProduction` directory.

## Portable Source Integrity Gate

Run `python scripts/verify_embedded_docs.py` after installation or migration. Any failure means the complete source documents are missing, truncated, or changed without updating `references/embedded-docs-manifest.json`; stop the pipeline until repaired.

## Pipeline Stages

1. Requirement intake
2. UX/UI spec generation
3. Visual design brief
4. Full-screen design mockup generation
5. Explicit human design approval
6. Requirement-to-approved-design semantic analysis
7. Approved-design-to-layout analysis
8. Asset and sheet planning
9. Production image generation
10. Sheet slicing
11. FairyGUI assembly planning
12. FairyGUI package resource staging
13. XML draft generation
14. Validation
15. FairyGUI editor publish
16. Unity import and smoke test

## Stage 1: Requirement Intake

Check whether the current requirement or conversation contains enough information.

Blocking information:

- Game or app type
- Target screen name
- Screen goal
- Main player/user operation
- Target framework when FairyGUI output is expected
- At least one reference image, with a declared role, when visual assets will be generated, redrawn, restyled, or reconstructed

Assumable defaults:

- Resolution: 1920x1080
- Orientation: landscape mobile
- Text: not baked into images
- Asset format: transparent PNG for isolated assets
- Sheet naming: lowercase snake_case
- FairyGUI output: draft XML plus editor checklist

If blocking information is missing, ask concise questions before generating formal documents.

## Stage 2: UX/UI Spec

Create `specs/ui_spec.md` with:

- confirmed information
- temporary assumptions
- open questions
- out-of-scope items
- screen goal
- player flow
- component list
- state matrix
- art direction and negative constraints
- asset needs
- acceptance criteria

## Stage 3: Visual Design Brief

When a complete screen is created from requirements or design documents, read `references/design-mockup-approval-contract.md` and create `specs/visual_design_brief.md`.

The brief must connect requirements, UI/UX documents, and reference images to:

- complete-screen composition
- functional regions
- required components and states
- visual hierarchy
- perspective, lighting, palette, and material direction
- text and localization policy
- asset-separation constraints
- negative constraints
- mockup acceptance criteria

Do not call image generation for a complete-screen mockup until this brief exists.

## Stage 4: Full-Screen Design Mockup Generation

Generate one or more complete-screen design proposals under `generated/design/`.

After generation:

- create `reports/design_draft_review.md`
- create or update `reports/design_approval.json` with `status=pending`
- present the exact generated file to the user
- stop the pipeline

Do not generate semantic maps, layout specs, asset manifests, sheets, FairyGUI plans, or XML in the same uninterrupted run.

## Stage 5: Explicit Human Design Approval

Run:

```bash
python scripts/check_design_approval.py --root UIProduction --stage semantic_analysis --out UIProduction/reports/design_gate_report.json --report-md UIProduction/reports/design_gate_blocking_report.md
```

Rules:

- the AI may not approve its own design
- approval must identify the exact file
- approval must include the exact file SHA-256
- changed image bytes invalidate approval
- `approvedFor` must contain the requested next stage
- silence, inferred preference, or generic continuation is not approval

If the gate fails, output `设计稿确认阻塞报告` and remain in the design/revision stage.

## Stage 6: Requirement-To-Approved-Design Semantic Analysis

After approval, read `references/uxui-semantic-contract.md` and create project-specific files before layout:

- `specs/uxui_semantic_spec.md`
- `specs/component_state_map.json`
- `reports/semantic_layout_consistency_report.md` when comparing existing layout/specs

Rules:

- Identify what each visible part is, what it does, and which requirement it supports.
- Identify component reuse before naming layout objects.
- If two visible objects are the same component in different states, map them to the same `componentType` with different `instanceId` and `stateVariant`.
- Record whether business state is owned by GamePlay/Config, visual state by FairyGUI Controller/Gear, and continuous runtime data by GameUI.
- Use `references/semantic-controller-mapping-contract.md` to decide which objects require Controllers, which visual properties require Gears, and which values must stay runtime-bound.
- Use `references/component-instance-configuration-contract.md` to define every reusable visual instance's `xmlInstanceName`, `controllerPages`, implementation mode, component file, preview values, and runtime bindings.
- Use `references/visual-part-coverage-contract.md` to create `component_visual_parts.json` from the approved design. Record every required visible icon, frame, title decoration, background, separator, marker, loader, and text part with a project-defined role and explicit implementation.
- Reusable instances that differ in role, selected state, title, icon, or preview data must not all use one unconfigured default component.
- A required visible part may not disappear merely because it is non-interactive or visually small.
- Run `scripts/validate_semantic_controller_mapping.py --root UIProduction --stage semantic_analysis` before layout work.
- Record visible design elements that are not supported by requirements and requirements that are not visible in the design.

The approved design image must be named as the visual source in `uxui_semantic_spec.md`.

## Stage 7: Approved-Design-To-Layout Analysis

When an approved design image is the layout source, first run the approval gate for `layout_analysis`, then read `references/design-to-layout-contract.md` and create project-specific files before slicing or XML. Write them under the current project's `UIProduction` tree, not inside the reusable skill:

- `specs/layout_spec.json`
- `specs/slice_plan.json`
- `reports/layout_overlay_review.md` or `layout_overlay_preview.png`

Rules:

- Layout objects must reference semantic output when it exists: `semanticId`, `componentType`, `instanceId`, `stateVariant`, `stateOwner`, `runtimeRole`, and `requirementIds`.
- AI may infer regions, objects, slots, and likely component ownership.
- Do not directly slice stateful or interactive objects from a flat screenshot.
- Do not generate main panel XML until `component_state_map.json`, `layout_spec.json`, and `slice_plan.json` agree with `fgui_spec.md`.
- If overlay preview cannot be generated, mark the layout as needing visual review and treat XML as blocked unless the user accepts the risk.
- Run `scripts/validate_semantic_controller_mapping.py --root UIProduction --stage layout_analysis`; unresolved state ownership or state variants block assembly.

## Stage 8: Asset and Sheet Planning

Run the approval gate for `asset_planning`, read `references/visual-reference-contract.md` and `references/asset-size-contract.md`, then create `manifests/asset_manifest.json` and `specs/sheet_plan.md`.

The manifest owns:

- visual-production intent and reference-image declarations
- asset names
- file names
- source pixel dimensions
- FairyGUI display dimensions
- scale policy and render mode
- pivot
- states
- sheet/cell placement
- transparent/trim/padding requirements
- FairyGUI package/layer/component mapping

The sheet plan owns:

- sheet dimensions
- row/column layout
- per-cell item list
- imagegen prompt batches
- negative prompt constraints

## Stage 9: Production Image Generation

Do not enter this stage without both a valid primary reference image and a passing approval gate for `resource_generation`. The reference controls art direction; the approved full-screen design controls screen composition and layout intent.

Use image generation for:

- background images
- operation tables or environment pieces
- isolated UI objects
- transparent sprite sheets
- visual mockups

Do not use image generation for:

- exact diagrams
- final XML
- localization text
- information that must be numerically exact

Always keep production sheets simple: one item per cell, no cross-cell shadows, no baked labels.

## Stage 10: Sheet Slicing

Input:

- generated sheet PNG
- `asset_manifest.json`

Output:

- named transparent PNGs
- `reports/cut_report.json`
- preview contact sheet

Acceptance checks:

- file names match manifest
- transparent background exists where required
- object is not cropped
- no unintended neighboring pixels
- required padding is preserved
- real output pixels equal `sourcePixelSize`
- target FairyGUI size equals `displaySize`
- scaling behavior is explicitly declared by `scalePolicy`
- dimensions and pivots match manifest

## Stage 11: FairyGUI Assembly Planning

Run the approval gate for `fairygui_assembly`, then create `specs/fgui_spec.md` before XML.

It must include:

- package name and package id
- component list
- semantic component mapping from `component_state_map.json`
- display list hierarchy
- resource reference table
- layout region table: each visual region's bounds, parent component, anchor/relation strategy, and whether it is static, interactive, or runtime-filled
- slot table: customer slots, ingredient cells, equipment slots, plate slots, takeout slots, drag/drop hit areas, and their stable names, xy, size, pivot, semantic IDs, and binding IDs
- component ownership table: which component owns each state, hit area, drag target, list item, and reusable visual element
- controller table derived from requirement-defined and design-visible discrete states
- gear mapping table: controller/page to object visibility, icon, text, position, size, look, color, animation, or font-size changes
- requirement IDs and state-owner columns in Controller and Gear tables
- transition table
- relation/adaptation rules
- mandatory Instance Configuration table covering every `component_state_map.visualInstances` entry
- mandatory Visual Part Coverage table covering every `component_visual_parts.json` entry
- external component parameter table for Button/Label instance title, icon, selected-state, and localization overrides
- readable editor-preview values and localization-key storage strategy
- text/localization rules
- Unity binding fields
- automation risk notes

Before XML readiness, run `scripts/validate_semantic_controller_mapping.py --root UIProduction --stage fairygui_assembly`. Missing Controller pages or Gear rows are blockers, not documentation warnings.

## Stage 12: FairyGUI Package Resource Staging

Read `references/package-resource-path-contract.md` before writing XML.

For each file-backed resource:

- declare `asset.packageRelativeFile`
- require `asset.file == package.outputPath/packageRelativeFile`
- copy or generate the resource under `fgui_xml/<package>/<packageRelativeFile>`
- verify the exact staged file exists under the future `package.xml` directory
- keep project-root paths out of package-local XML

The package directory is an atomic import bundle. Do not copy XML and image files through unrelated partial lists.

Example:

```text
asset.file: fgui_xml/twinbound_v2/art/icon_anvil.png
package.outputPath: fgui_xml/twinbound_v2
packageRelativeFile: art/icon_anvil.png
```

Only `art/icon_anvil.png` may be used by package-local XML.

## Stage 13: XML Draft Generation

Before generation, run `scripts/validate_semantic_controller_mapping.py --stage xml_generation`, then run `scripts/check_xml_readiness.py`. Use `--require-design-approval` when the full-screen design was generated from requirements/design documents, use `--resource-generation` when this pipeline generated or redrew visual assets, and use `--design-driven` when a design image is part of the layout source. Stop on any blocker.

Generate:

- `reports/xml_readiness_report.json`
- `reports/xml_generation_input_snapshot.json`
- `fgui_xml/<package>/package.xml`
- component XML drafts
- updated `manifests/fgui_id_registry.json`

Rules:

- Do not generate a main panel XML from a design image until `uxui_semantic_spec.md`, `component_state_map.json`, `layout_spec.json`, `slice_plan.json`, and `fgui_spec.md` agree.
- Select `fresh` for new XML or `editor-compatible` only for XML already accepted/cleaned/exported by FairyGUI editor.
- Use stable IDs from the registry and register new IDs before XML references them.
- Generate in dependency order: `package.xml`, leaf components, composite components, main panel.
- Register every referenced component/image in `package.xml`.
- For external `<Button .../>` and `<Label .../>` instance parameters, require the target component `extention` to match, validate allowed fields, and resolve all `ui://` values.
- For each visual instance, materialize the declared implementation mode. `variant_component` must point to a registered XML whose default Controller pages match `controllerPages`; `controller_pages` requires editor-verified encoding; `runtime_binding` requires readable preview fallback; `static_default` is allowed only for intentionally identical instances.
- For each required visual part, materialize the declared Manifest asset or XML node. Detailed Graph fallbacks require explicit human approval.
- Do not leave visible `@ui_...` keys in approved-design editor previews unless a verified editor localization plugin resolves them. Store the localization key separately, such as in `customData`.
- Generate `package.xml path + name` from `packageRelativeFile`, never from the UIProduction-root-relative `file` field.
- Generate same-package image `fileName` as the exact `packageRelativeFile`.
- Use resource IDs in `src`; do not use file names as `src`.
- Every fresh image node must declare `size` equal to Manifest `displaySize`.
- Real image dimensions must equal `sourcePixelSize`; unexplained scaling is forbidden.
- Use `ui://<package_id><resource_id>` for component URLs.
- Keep generated transitions conservative unless the user gives exact timing.

## Stage 14: Validation

Run `scripts/validate_pipeline.py` and write `reports/pipeline_validate_report.json`.

Run `scripts/validate_fgui_xml.py` with `--manifest`, `--registry`, and `--mode fresh` for new XML. The validator must resolve every `package.xml path + name` and image `fileName` against the exact package directory; basename-only matches are forbidden in fresh mode. After FairyGUI editor cleanup/export, rerun with `--mode editor-compatible` and keep a separate report.

Also manually inspect:

- reference-image roles and layout-source consistency
- actual image pixels, Manifest source/display sizes, layout bbox sizes, and XML image sizes
- semantic map to layout consistency
- XML opening in FairyGUI editor
- missing resource warnings
- controller/page names
- relation behavior at target resolutions
- text fields, readable preview text, and localization keys
- repeated component instances use the intended portraits, icons, titles, states, and default Controller pages
- all required visual parts from `component_visual_parts.json` are visible, including small icons and non-interactive framing/decorative elements
- no white placeholder blocks, blank buttons, raw localization keys, duplicated default content, or silently omitted frames/titles/icons remain
- list default item URLs

## Stage 15: Editor Publish

FairyGUI editor publish remains the official final output step.

Generated XML is considered a draft until:

- editor opens the package
- a preview screenshot is captured at the design resolution and compared with the approved design
- repeated semantic instances are visibly distinct as specified
- no raw localization keys, blank controls, white placeholder blocks, or unintended default-component duplicates remain
- visual layout is checked
- package is published
- Unity can load the published package

## Stage 16: Unity Smoke Test

Check:

- `UIPackage.AddPackage`
- main component creation
- expected named children exist
- controllers can be switched
- buttons dispatch events
- list items instantiate
- loaders resolve expected resources

## Rework Rules

- Rework only the failed scope when possible: one full-screen design draft, one semantic component, one state group, one asset, one sheet, one component, or one controller.
- Any change to an approved full-screen design invalidates its hash-bound approval and returns the pipeline to Stage 5.
- Do not regenerate all IDs during a rework.
- Do not rename assets unless the manifest changes first.
- Update the report with what changed and why.
