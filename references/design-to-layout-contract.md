# Design To Layout Contract

Use this contract when a user wants to turn an explicitly approved design image into FairyGUI layout, slicing, and XML.

## Core Rule

Do not generate FairyGUI XML directly from a design image.

When the design was generated from requirements or design documents, first run `scripts/check_design_approval.py --stage layout_analysis`. A draft, pending, rejected, superseded, modified, or AI-self-approved image is not a valid layout source.

Do not treat visual boxes as semantic truth. When requirements exist, read `references/uxui-semantic-contract.md`, `references/semantic-controller-mapping-contract.md`, and `references/component-reuse-parameterization-contract.md` first and use `component_state_map.json` as the semantic source of truth. Components with the same hierarchy must share a base component even when their titles, icons, portraits, values, colors, sizes, or default pages differ. Also read `references/visual-part-coverage-contract.md` and create `component_visual_parts.json` before asset planning, so small icons, frames, title decorations, backgrounds, separators, and markers cannot disappear between layout analysis and XML. Read `references/asset-isolation-contract.md` before assigning slice policies: the complete mockup is not a runtime background or universal crop sheet, and a crop cannot remove UI, create transparency, clean neighboring pixels, or reconstruct hidden content by itself.

Keep this contract generic. It defines required files, fields, gates, and review rules. It must not contain project-specific screen names, concrete coordinates, asset file names, package IDs, resource IDs, or component instance IDs. Store those in the active project's `UIProduction` directory.

The required flow is:

```text
requirement document + approved design image + design_approval.json
-> approval gate
-> uxui_semantic_spec.md
-> component_state_map.json
-> component_visual_parts.json
-> layout_spec.json
-> layout overlay preview
-> user or visual QA confirmation
-> slice_plan.json
-> asset_manifest.json / fgui_id_registry.json
-> production_preview_lineage.json / typography_spec.json
-> exact production preview assembled from staged runtime assets
-> production_preview_approval.json
-> fgui_spec.md
-> XML draft generation
-> XML validation and FairyGUI editor check
```

AI may infer layout, object boundaries, likely component ownership, and rough coordinates. Scripts or deterministic transforms must own slicing, file naming, ID assignment, and XML emission.

## Required Intermediate Files

For project-specific work, store these beside the project's UI production specs, for example `Docs/UIProduction/<screen>/specs/`:

- `design_approval.json`: exact approved image, SHA-256, human confirmation, and approved downstream scope.
- `uxui_semantic_spec.md`: purpose, requirement links, component reuse, states, runtime ownership.
- `component_state_map.json`: machine-readable mapping from visible instances to reusable component types, `reusePlan`, state variants, parameter fields, child components, and any justified structural variants.
- `component_visual_parts.json`: machine-readable inventory of every required visible part, implementation mode, Manifest asset or XML node, file scope, complexity, and fallback policy.
- `layout_spec.json`: canvas, regions, objects, slots, coordinate source, confidence, and review status.
- `slice_plan.json`: exact crop candidates, extraction method, output names, and whether a crop is automatic, cleanup-required, or forbidden.
- `production_preview_lineage.json`: exact mapping from every runtime bitmap to its usage in the final production preview.
- `typography_spec.json`: deterministic text styles and component-local text bounds shared by preview and XML.
- `layout_overlay_preview.png`: visual overlay of regions and object boxes on the design image.

Do not store these project-specific outputs inside the reusable skill unless they are deliberately generic examples with placeholder names and no real project IDs.

## layout_spec.json Requirements

Required top-level fields:

- `version`
- `screen`
- `designResolution`
- `sourceImages`: must include the exact approved full-screen design image; art-style references alone are not valid layout sources
- `semanticSources`
- `coordinateSystem`
- `regions`
- `objects`
- `slots`
- `relations`
- `reviewStatus`
- `blockingForXml`

Region fields:

- `name`
- `bbox`: `[x, y, width, height]` in design resolution coordinates
- `type`: `static`, `interactive`, `runtime_filled`, or `overlay`
- `parent`
- `semanticPurpose`
- `requirementIds`
- `relation`
- `interactionResponsibility`

Object fields:

- `name`
- `semanticId`
- `instanceId`
- `componentType`
- `stateVariant`
- `nodeType`: `image`, `component`, `loader`, `text`, `list`, `group`, or `graph`
- `component` when nodeType is `component`
- `region`
- `bbox`
- `binding`
- `stateOwner`
- `runtimeRole`
- `zLayer`: `background`, `content`, `foreground`, `overlay`, `modal`, or `debug`
- `occlusionPolicy`: `opaque_background`, `normal`, `transparent_frame`, `intentional_overlay`, `modal_blocker`, or `non_visual`
- `requirementIds`
- `slicePolicy`: `slice_static`, `use_component`, `use_manifest_asset`, `runtime_generated`, or `do_not_slice`
- `assetName`: required for bitmap/image objects; must resolve to `asset_manifest.json.assets[].name`
- `sizeSource`: normally `asset_manifest.displaySize`

For every image object, `bbox[2:4]` must equal the resolved asset's `displaySize`. Do not apply undocumented per-instance scaling. If the same bitmap is intentionally needed at different design sizes, create distinct manifest entries or a documented reusable component strategy before XML generation.

Slot fields:

- `slotId`
- `componentName`
- `componentType`
- `stateVariant`
- `region`
- `bbox`
- `pivot`
- `binding`
- `stateOwner`
- `runtimeRole`
- `zLayer`
- `occlusionPolicy`
- `requirementIds`

## Same Component / Different State Rule

If the design shows two copies of the same semantic component in different states, do not create two unrelated layout objects.

Correct:

```json
{"instanceId":"plate_empty_1","componentType":"PlateSlot","stateVariant":"empty"}
{"instanceId":"plate_ready_1","componentType":"PlateSlot","stateVariant":"ready"}
```

Wrong:

```json
{"componentType":"EmptyPlate"}
{"componentType":"BurgerPlate"}
```

The first form can map to one FairyGUI component with controllers/gears. The second form incorrectly bakes state into component identity. The same rule applies to title, icon, portrait, number, color, instance size, and localization differences: these are instance parameters, not component identities. When a fixed visual page differs by instance, prefer an exported Controller passed from the parent through `controller="name,pageIndex"`.

## slice_plan.json Requirements

Every slice entry must say whether it is safe to cut from the design image.

Allowed extraction modes:

- `direct_crop`: static, already self-contained area cut directly from an approved full-screen design; no dynamic objects, neighboring pixels, baked text, occlusion, or required alpha extraction.
- `exact_crop`: runtime pixels are exactly `[x,y,width,height]` from the declared approved resource-preview sheet, with no resize, cleanup, or reinterpretation.
- `deterministic_transform`: a declared and hash-frozen processor performs trim, alpha cleanup, resize, or another reproducible transform from the exact declared resource-preview sheet.
- `crop_after_cleanup`: planning-only label before a concrete processor exists; it must be resolved to `deterministic_transform` with script evidence before `sheet_slicing`.
- `from_sheet`: planning-only source classification; it is not a final derivation mode and must become `exact_crop` or `deterministic_transform` for every `approved_sheet_slice` asset.
- `from_existing_fgui`: source already exists in a FairyGUI package.
- `image_generation_with_reference`: separately generated clean background, isolated subject/icon, or content-free skin using the approved design as reference.
- `manual_reconstruction`: reviewed reconstruction with explicit evidence.
- `inpainted_environment`: reviewed environment-only result that reconstructs pixels hidden by UI or subjects.
- `do_not_slice`: dynamic, stateful, interactive, runtime content, or a full-screen reference-only image.

For every final `approved_sheet_slice` row, `sourceFile`, `crop`, `output`, and `extractionMode` must exactly match Manifest and `cut_report.json`. The source file must be the actual bitmap opened by the slicer, including any `_alpha` or `_clean` suffix.

Forbidden direct slicing from a flat design image:

- the complete approved design as a runtime environment background
- backgrounds whose UI/characters must be removed or whose hidden pixels must be reconstructed
- portraits, characters, icons, badges, or emblems that require transparent isolation or neighbor cleanup
- panel, card, row, bar, frame, or button skins that include dynamic text, values, state content, or reusable child components
- button pressed/disabled/hover states
- controller states not visible in the screenshot
- customer expression states
- equipment cooking/ready/overcook states
- drag/drop valid/invalid feedback
- dynamic list items
- text and numeric UI

## XML Gate

Main panel XML cannot be generated from a design image unless all are available and consistent:

- `design_approval.json` passes for `xml_generation`
- the approved image file exists and its SHA-256 still matches
- `uxui_semantic_spec.md`
- `component_state_map.json`
- `component_visual_parts.json`
- `layout_spec.json`
- `slice_plan.json`
- `asset_manifest.json` with `sourcePixelSize`, `displaySize`, `scalePolicy`, and `renderMode` for every bitmap
- `fgui_id_registry.json`
- `fgui_spec.md`
- a passing `scripts/validate_semantic_controller_mapping.py --stage xml_generation` report
- a passing `scripts/validate_component_reuse.py --stage xml_generation` report
- a passing `scripts/validate_display_list_z_order.py --stage xml_generation` report
- a passing `scripts/validate_bitmap_asset_provenance.py --stage xml_generation` report
- a passing `scripts/validate_asset_isolation.py --stage xml_generation` report and human `asset_isolation_review.md`
- a passing `scripts/validate_production_preview_lineage.py --stage xml_generation` report and human `production_preview_approval.json`
- a passing `scripts/validate_typography_fidelity.py --stage xml_generation` report
- a passing `scripts/validate_visual_part_coverage.py --stage xml_generation` report
- full FairyGUI XML parsing specification
- either `layout_overlay_preview.png` reviewed, or a written risk acceptance that overlay review was skipped

If any item is missing, output an XML blocking report instead of XML.

## Review Output

When reviewing a design-to-layout pass, report:

- visual instances whose semantic component/state is ambiguous
- same-component/different-state cases that were split incorrectly
- large backgrounds or opaque containers placed after normal content in XML order
- foreground frames incorrectly classified as opaque backgrounds
- components split only because title, icon, portrait, value, color, size, localization, or selected page differs
- repeated substructures that should become parameterized child components
- regions and slots with low confidence
- objects marked `do_not_slice`
- crops requiring cleanup
- slice rows whose reason claims transparent isolation, UI removal, separated text, clean background, or reconstruction while the extraction method is only a rectangular crop
- full-screen mockups incorrectly registered as runtime backgrounds or package assets
- portraits/icons with opaque screenshot rectangles or neighboring pixels
- panel/button/frame skins containing baked dynamic text or child component content
- final preview assets that are look-alike regenerated resources rather than exact staged runtime files
- production assets changed after production-preview approval
- preview scripts and XML using different font identities, sizes, colors, spacing, strokes, shadows, or text bounds
- mismatches between the approved design file and `layout_spec.json.sourceImages`
- changed design bytes whose SHA-256 no longer matches approval
- image objects whose `assetName` is missing or unresolved
- required visual parts missing from Manifest, `fgui_spec.md`, or component XML
- detailed visual parts silently downgraded to Graph without human approval
- mismatches between Manifest `displaySize` and layout `bbox` size
- mismatches between `component_state_map.json`, `layout_spec.json`, `fgui_spec.md`, and existing XML
- requirement-defined states missing from semantic components or Controller pages
- stateful objects whose `stateOwner` conflicts with semantic ownership
- semantic Gear requirements missing from `fgui_spec.md` or component XML
- changes needed before XML generation
