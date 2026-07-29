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

## Mandatory Stage Timing

Read `references/pipeline-stage-timing-contract.md` and initialize timing before Stage 1:

```bash
python scripts/record_pipeline_timing.py --root UIProduction init
```

Before entering each canonical stage, run `start --stage <stage_id>`. Immediately after the stage completes, blocks, or fails, run `finish` with the matching status and produced artifacts. Use `skip` only when a stage is genuinely outside the agreed scope.

Only one stage may be running at a time. Rework creates another attempt for the same stage with `--rework`; it must not overwrite the earlier duration.

Stage 5 is normally `waiting` time. Stages 15 and 16 are normally `external` time. The final report must keep active processing, human waiting, and external-tool time separate.

Every command updates:

```text
reports/pipeline_stage_timings.json
reports/pipeline_stage_timings.md
```

A timing snapshot may be generated while approval or external work is pending:

```bash
python scripts/record_pipeline_timing.py --root UIProduction snapshot
```

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

- finish `design_mockup_generation`
- start `design_approval` so the human wait is measured separately
- create `reports/design_draft_review.md`
- create or update `reports/design_approval.json` with `status=pending`
- present the exact generated file to the user
- write a timing snapshot
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

If the gate fails, finish the current `design_approval` attempt as `blocked`, output `设计稿确认阻塞报告`, and remain in the design/revision stage. A later approval or revision starts a new attempt with `--rework`.

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
- Read `references/component-reuse-parameterization-contract.md` before choosing component files. Every reusable component must declare a `reusePlan`; title, icon, portrait, number, color, size, localization, or selected-page differences must remain parameters rather than separate XML files.
- Use `references/component-instance-configuration-contract.md` to define every reusable visual instance's `xmlInstanceName`, `controllerPages`, implementation mode, component file, preview values, and runtime bindings.
- Use `references/visual-part-coverage-contract.md` to create `component_visual_parts.json` from the approved design. Record every required visible icon, frame, title decoration, background, separator, marker, loader, and text part with a project-defined role and explicit implementation.
- Reusable instances that differ in role, selected state, title, icon, or preview data must not all use one unconfigured default component, but they also must not be split into near-identical variants merely to preserve those values.
- Prefer external Button/Label parameters, exported Controller pages, runtime binding, and reusable child components. For fixed per-instance pages, require target `controller@exported=true` and parent `controller="name,pageIndex"`. Allow `variant_component` only for a material structural or verified compatibility difference.
- A required visible part may not disappear merely because it is non-interactive or visually small.
- Run `scripts/validate_semantic_controller_mapping.py --root UIProduction --stage semantic_analysis` and `scripts/validate_component_reuse.py --root UIProduction --stage semantic_analysis` before layout work.
- Classify every layout object with `zLayer` and `occlusionPolicy`; backgrounds are backmost and use the lowest XML order.
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

Run the approval gate for `asset_planning`, read `references/visual-reference-contract.md`, `references/asset-size-contract.md`, `references/bitmap-icon-source-contract.md`, `references/asset-isolation-contract.md`, `references/production-preview-lineage-contract.md`, and `references/typography-fidelity-contract.md`, then create `manifests/asset_manifest.json`, `specs/sheet_plan.md`, `specs/production_preview_lineage.json`, and `specs/typography_spec.json`.

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
- approved bitmap provenance in `assetSource` for every icon-like asset
- `production.requiresAssetIsolation=true` for complete-screen projects
- `production.requiresProductionPreviewLineage=true` and `production.requiresTypographyFidelity=true`
- per-bitmap `assetIsolation`: role, transparency requirement, neighbor-pixel policy, baked-content policy, source containment, occlusion policy, review status, and review evidence
- exact preview usage and runtime-file identity for every bitmap
- per-bitmap `sourceLineage`: exact approved source, exact provided source, or reference reconstruction; exact file/crop or deterministic transform; source and transform hashes
- deterministic text style and bounds for every text instance, including `hostComponentFile`/`hostInstanceName` when a reused Button/Label instance overrides title style
- deterministic typography render-trace path and per-instance render evidence

The sheet plan owns:

- exact resource-preview sheet file paths
- sheet dimensions
- row/column layout
- per-cell item list
- imagegen prompt batches
- negative prompt constraints
- human review target/evidence for every sheet used by `approved_sheet_slice`

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

The complete approved UI mockup is a composition reference, not a runtime background or universal crop sheet. Generate or reconstruct clean environment-only backgrounds separately. Portraits and icons must be genuinely isolated; panels, frames, bars, rows, cards, and buttons must not include dynamic text, state values, or reusable child content.

A new image-generation call after design approval may create production assets, but those assets are only candidates until the final production preview is assembled from their exact staged files. Do not approve a newly generated full-screen reinterpretation as though it proved which runtime pixels will ship.

Before regenerating anything, apply source priority:

1. exact user/project-provided production bitmap;
2. exact self-contained crop from the approved design;
3. deterministic transform of a frozen source;
4. reference reconstruction only when exact extraction is impossible.

Record the chosen relation and derivation in `production_preview_lineage.json.assets[].sourceLineage`. Reference reconstruction requires an explicit reason and may not claim pixel identity with the approved design.

Run `scripts/validate_asset_isolation.py --root UIProduction --stage resource_generation` after bitmap output and before assembly. The automated report and `reports/asset_isolation_review.md` must pass.

## Stage 10: Sheet Slicing

Input:

- generated sheet PNG
- `asset_manifest.json`

Output:

- named transparent PNGs
- `reports/cut_report.json`
- preview contact sheet

Acceptance checks:

- every `approved_sheet_slice` has one final per-asset slice row using `exact_crop` or `deterministic_transform`
- `manifest.sheets[].file`, `assetSource.sourceFile`, `slice_plan.sourceImages/sourceFile`, `cut_report.outputs[].sourceFile`, and `sourceLineage.sourceFile` identify the same actual resource-preview bitmap
- processed `_alpha`/`_clean` sheets are registered and reviewed under their real filenames
- `cut_report.json` freezes exact crop, output path, source/output hashes, and processor-script hash when applicable
- file names match manifest
- transparent background exists where required
- object is not cropped
- no unintended neighboring pixels
- required padding is preserved
- real output pixels equal `sourcePixelSize`
- target FairyGUI size equals `displaySize`
- scaling behavior is explicitly declared by `scalePolicy`
- dimensions and pivots match manifest
- no full-screen UI is embedded in a background
- no portrait/icon is an opaque rectangular screenshot crop
- no panel/button/frame skin contains baked dynamic text or reusable child content
- every sliced output is the exact file that will be staged and used by the production preview
- `production_preview_lineage.json` records the staged file, source relation, derivation mode, source/crop/transform evidence, and future SHA-256
- exact crops are pixel-equal to the declared source region; deterministic transforms freeze and identify the real processor; generated-sheet outputs declare reference reconstruction relative to the approved screen
- `validate_asset_isolation.py --stage sheet_slicing` passes with review evidence

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
- controller table derived from requirement-defined and design-visible discrete states, including whether each Controller is exported
- gear mapping table: controller/page to object visibility, icon, text, position, size, look, color, animation, or font-size changes
- requirement IDs and state-owner columns in Controller and Gear tables
- transition table
- relation/adaptation rules
- mandatory Component Reuse Plan table covering every reusable semantic component
- mandatory Instance Configuration table covering every `component_state_map.visualInstances` entry, including Controller Parameters
- mandatory Visual Part Coverage table covering every `component_visual_parts.json` entry
- external component parameter table for Button/Label instance title, icon, selected-state, and localization overrides
- readable editor-preview values and localization-key storage strategy
- text/localization rules
- Unity binding fields
- automation risk notes

Before XML readiness, run `scripts/validate_semantic_controller_mapping.py --root UIProduction --stage fairygui_assembly`, `scripts/validate_component_reuse.py --root UIProduction --stage fairygui_assembly`, `scripts/validate_display_list_z_order.py --root UIProduction --stage fairygui_assembly`, `scripts/validate_bitmap_asset_provenance.py --root UIProduction --stage fairygui_assembly`, `scripts/validate_asset_isolation.py --root UIProduction --stage fairygui_assembly`, `scripts/validate_production_preview_lineage.py --root UIProduction --stage fairygui_assembly`, and `scripts/validate_typography_fidelity.py --root UIProduction --stage fairygui_assembly`. Missing Controller exports/parameters, Gear rows, reuse plans, back-to-front layer declarations, bitmap provenance, resource isolation evidence, exact preview lineage, deterministic typography, or justified structural differences are blockers.

## Stage 12: FairyGUI Package Resource Staging

Read `references/package-resource-path-contract.md` before writing XML.

For each file-backed resource:

- declare `asset.packageRelativeFile`
- require `asset.file == package.outputPath/packageRelativeFile`
- copy or generate the resource under `fgui_xml/<package>/<packageRelativeFile>`
- verify the exact staged file exists under the future `package.xml` directory
- keep project-root paths out of package-local XML

The package directory is an atomic import bundle. Do not copy XML and image files through unrelated partial lists.

After staging, assemble `generated/preview/<screen>_production.png` from the exact package files. Render text from `specs/typography_spec.json` or capture the actual FairyGUI component; do not hardcode a separate font/color/size table in the preview script. Reused Button/Label instances with different title styles must materialize matching parent `titleFontSize/titleColor/title` overrides and declare their host instance in the Typography Spec. For deterministic overlays, the same render execution must write `reports/typography_render_trace.json` with the current typography-spec SHA-256 and one exact entry per rendered text instance.

Create a pending production-preview approval record and stop:

```bash
python scripts/record_production_preview_approval.py --root UIProduction --action pending --note "Waiting for exact production preview approval"
```

After explicit human approval, record the preview and runtime-asset hashes. Any subsequent asset or typography change supersedes that approval.

Example:

```text
asset.file: fgui_xml/twinbound_v2/art/icon_anvil.png
package.outputPath: fgui_xml/twinbound_v2
packageRelativeFile: art/icon_anvil.png
```

Only `art/icon_anvil.png` may be used by package-local XML.

## Stage 13: XML Draft Generation

Before generation, run `scripts/validate_semantic_controller_mapping.py --stage xml_generation`, `scripts/validate_component_reuse.py --stage xml_generation`, `scripts/validate_display_list_z_order.py --stage xml_generation`, `scripts/validate_bitmap_asset_provenance.py --stage xml_generation`, `scripts/validate_asset_isolation.py --stage xml_generation`, `scripts/validate_production_preview_lineage.py --stage xml_generation`, `scripts/validate_typography_fidelity.py --stage xml_generation`, and `scripts/validate_visual_part_coverage.py --stage xml_generation`, then run `scripts/check_xml_readiness.py`. Use `--require-design-approval` when the full-screen design was generated from requirements/design documents, use `--resource-generation` when this pipeline generated or redrew visual assets, and use `--design-driven` when a design image is part of the layout source. Stop on any blocker.

Generate:

- `reports/component_reuse_report.json`
- `reports/component_reuse_report.md`
- `reports/display_list_z_order_report.json`
- `reports/display_list_z_order_report.md`
- `reports/bitmap_asset_provenance_report.json`
- `reports/bitmap_asset_provenance_report.md`
- `reports/asset_isolation_report.json`
- `reports/asset_isolation_report.md`
- `reports/asset_isolation_review.md`
- `reports/production_preview_approval.json`
- `reports/production_preview_lineage_report.json`
- `reports/production_preview_lineage_report.md`
- `reports/typography_render_trace.json`
- `reports/typography_fidelity_report.json`
- `reports/typography_fidelity_report.md`
- `reports/xml_readiness_report.json`
- `reports/xml_generation_input_snapshot.json`
- `fgui_xml/<package>/package.xml`
- component XML drafts
- updated `manifests/fgui_id_registry.json`

Rules:

- Do not generate a main panel XML from a design image until `uxui_semantic_spec.md`, `component_state_map.json`, `layout_spec.json`, `slice_plan.json`, and `fgui_spec.md` agree.
- Select `fresh` for new XML or `editor-compatible` only for XML already accepted/cleaned/exported by FairyGUI editor.
- Use stable IDs from the registry and register new IDs before XML references them.
- Generate in dependency order: `package.xml`, reusable leaf components, reusable parameterized child components, base composite components, justified structural variants, main panel.
- Register every referenced component/image in `package.xml`.
- Emit each component `<displayList>` back-to-front: opaque backgrounds first, normal content next, transparent frames/overlays only after content.
- Never synthesize art-directed icons with Graph, SVG, font glyphs, PIL/ImageDraw, or other procedural vector-like drawing; use only approved bitmap sources recorded in Manifest.
- Never stage the complete approved design as a runtime background. Reject plain crop scripts that claim alpha extraction, UI removal, neighbor cleanup, text removal, or occlusion reconstruction. Require clean environment backgrounds, truly isolated subjects/icons, and content-free component skins.
- Never generate XML from an independently reinterpreted preview. The approved production preview must be composed from exact staged runtime assets, every asset must have valid source-lineage evidence, and its approval must still match all frozen hashes.
- Generate every text/richtext attribute and bound from `typography_spec.json`. The final preview renderer must use the same spec and produce a matching render trace; image-model lettering and unrelated hardcoded system-font settings are not XML truth.
- For external `<Button .../>` and `<Label .../>` instance parameters, require the target component `extention` to match, validate allowed fields, and resolve all `ui://` values.
- For each visual instance, materialize the declared implementation mode. Prefer `extension_override`, `controller_pages`, `runtime_binding`, or reusable children. `controller_pages` requires one exported target Controller, declared `controllerParameters`, and exact parent `controller="name,pageIndex"`. `variant_component` requires `reusePlan.strategy=variant_allowed`, a valid `variantJustification`, and a materially different XML structure; `static_default` is allowed only for intentionally identical instances.
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

Run `scripts/validate_pipeline.py` and write `reports/pipeline_validate_report.json`. Also retain the dedicated component-reuse, display-list z-order, bitmap-provenance, asset-isolation, production-preview-lineage, typography-fidelity, and visual-part reports.

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
- components that differ only by content or instance size use one base component plus parameters rather than duplicate XML variants
- repeated icon-plus-value, icon-plus-title, badge, row, or panel-shell structures are extracted as reusable child components when appropriate
- all required visual parts from `component_visual_parts.json` are visible, including small icons and non-interactive framing/decorative elements
- backgrounds contain environment only; isolated portraits/icons have clean alpha and no neighboring screenshot pixels; panel/button/frame skins contain no baked dynamic text or duplicate child content
- the visual preview uses the exact runtime asset files, not look-alike regenerated resources
- every exact source/crop claim is verified; every reconstructed asset is labeled as reconstruction and justified
- font identity, size, color, alignment, spacing, stroke/shadow, and text boxes match `typography_spec.json`, `typography_render_trace.json`, and XML
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

## Stage 17: Timing Finalization And Handoff

After all agreed production, editor, and Unity stages finish:

```bash
python scripts/record_pipeline_timing.py --root UIProduction finalize --status completed
python scripts/record_pipeline_timing.py --root UIProduction validate
```

`completed` is allowed only when all 16 canonical stages are `completed` or explicitly `skipped`. A blocked, failed, or incomplete run must be finalized as `blocked`, `failed`, or `partial` instead.

The final handoff must include:

- total wall-clock duration
- total active-processing duration
- total human-waiting duration
- total external-tool duration
- each stage's status, attempts, and duration
- `reports/pipeline_stage_timings.json`
- `reports/pipeline_stage_timings.md`

Do not reconstruct stage durations from memory or file timestamps after the flow ends.

## Rework Rules

- Rework only the failed scope when possible: one full-screen design draft, one semantic component, one state group, one asset, one sheet, one component, or one controller.
- Record every rework as a new timing attempt with `--rework`; preserve the failed or superseded attempt.
- Any change to an approved full-screen design invalidates its hash-bound approval and returns the pipeline to Stage 5.
- Do not regenerate all IDs during a rework.
- Do not rename assets unless the manifest changes first.
- Update the report with what changed and why.
