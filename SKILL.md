---
name: fairygui-ui-pipeline
description: Create and operate a semi-automated game UI production pipeline for FairyGUI. Use when the user wants to turn game UI requirements, UX/UI ideas, full-screen design mockups, imagegen outputs, sprite sheets, manifests, sliced PNG assets, existing design drafts, or FairyGUI XML rules into FairyGUI-ready specs, approved visual sources, semantic UX/UI maps, layout specs, asset plans, XML drafts, validation reports, controller/transition plans, and Unity binding notes. This skill must generate and explicitly approve a complete-screen mockup before downstream production when building a screen from requirements, enforce semantic/state mapping before layout work, and enforce XML strict mode before producing package.xml or component XML.
---

# FairyGUI UI Pipeline

## Highest Priority Rule

Do not invent FairyGUI XML.

The two complete source documents are embedded inside this skill and must be read from the skill directory, not from an external machine-specific path:

1. Read `references/fairygui-ai-generation-workflow.md` in full before operating the end-to-end UI production pipeline.
2. For any task that generates, reviews, repairs, or validates `package.xml` or component XML, read `references/fairygui-xml-parsing-specification.md` in full before XML work.
3. Read `references/fairygui-xml-parsing-spec.md` as the local alias/index for the embedded XML specification.
4. Read `references/fairygui-xml-contract.md` as the short gate.
5. Read `references/xml-strict-generation.md` as the XML production checklist.

Do not use this `SKILL.md`, memory, a summary, a bridge file, or a short contract as a replacement for either embedded complete source document.

## Operating Principles

- Do not jump directly from vague requirements to XML. First check whether requirements are sufficient.
- Do not jump directly from a design image to layout boxes. When requirements and a design image both exist, first create a semantic UX/UI pass that maps visible parts to purpose, component type, state, and runtime ownership.
- Keep the pipeline boundary strict: this skill stores generic workflow rules, schemas, gates, and validation logic only. Project-specific screen names, coordinates, component names, resource IDs, package IDs, asset paths, and design-image analysis results must live in that project's `UIProduction` directory.
- Treat `component_state_map.json` as the source of truth for whether two visible objects are the same component type in different states, or genuinely different components.
- Determine Controller, Gear, and runtime ownership from the combined requirement documents, UI/UX design documents, and exact approved design image. Never infer controller ownership from visual appearance alone.
- Treat `asset_manifest.json` as the single source of truth for asset names, sheet positions, source pixel sizes, FairyGUI display sizes, scale policies, states, pivots, and FairyGUI mapping.
- When visual assets will be generated, redrawn, restyled, or reconstructed, require at least one valid primary reference image and read `references/visual-reference-contract.md` before image generation.
- When a complete screen is created from requirements or design documents, read `references/design-mockup-approval-contract.md`, create a full-screen mockup, and stop for explicit human confirmation before semantic decomposition or any downstream production stage.
- The AI must never approve its own mockup. It may create `design_approval.json` with `pending` or `rejected`, but may write `approved` only after the user explicitly confirms the exact design file or a valid human approval record is provided.
- Read `references/asset-size-contract.md` before planning, slicing, registering, or placing bitmap resources. Unexplained differences between real pixels, manifest sizes, layout sizes, and XML sizes are errors.
- Read `references/package-resource-path-contract.md` before staging package files or writing XML. Project-root-relative `asset.file` and package-local `packageRelativeFile` are different paths and must never be substituted for each other.
- Read `references/component-reuse-parameterization-contract.md` before selecting component files. Reusable components must prefer one base XML plus external parameters, Controller pages, runtime bindings, or reusable child components. Title, icon, portrait, number, color, size, localization, or selected-page differences alone must not create separate variant XML files.
- Read `references/component-instance-configuration-contract.md` whenever reusable components appear more than once. Component-level Controller/Gear definitions are insufficient unless every semantic instance has a verifiable default-page, extension-override, exported Controller parameter, runtime-binding, or justified structural-variant strategy.
- Read `references/display-list-z-order-contract.md` before layout assembly or XML generation. FairyGUI displayList is back-to-front: opaque backgrounds must be the earliest XML children; later full-size components may appear only as explicitly transparent frames or intentional overlays.
- Read `references/bitmap-icon-source-contract.md` before producing small icons, badges, crests, or emblems. Production icons must use approved bitmap provenance; Graph/SVG/font-glyph/PIL geometry and other procedural vector-like substitutes are forbidden.
- Read `references/asset-isolation-contract.md` before planning or producing any bitmap from an approved full-screen mockup. The complete mockup is a reference, not a runtime background or universal crop sheet. Backgrounds must contain environment only; portraits and icons must be truly isolated; panel/button skins must not bake dynamic text or reusable child content. Every `approved_sheet_slice` must use the exact approved resource-preview sheet registered in `manifest.sheets` and listed in `slice_plan.sourceImages`; substituting a cleaned, alpha-adjusted, or alternate sheet without updating provenance is forbidden. Asset-isolation approval must identify a human reviewer and valid review type; AI/model self-approval is forbidden.
- Read `references/production-preview-lineage-contract.md` before final visual approval. The design mockup approval confirms composition/style; a second production-preview approval must freeze the exact staged runtime assets and their hashes. Every bitmap must also declare `sourceLineage`: exact approved-source crop, exact provided source, or explicit reference reconstruction. A production-ready supplied/self-contained source must be copied or cropped deterministically instead of regenerated into a look-alike.
- Read `references/typography-fidelity-contract.md` before creating final preview text or XML text nodes. Image-model lettering is reference-only. The production preview and FairyGUI XML must consume one deterministic `typography_spec.json` covering font, size, color, alignment, spacing, auto-size, stroke, shadow, text bounds, and localization mapping. Reused Button/Label instances with different title size/color must declare `hostComponentFile` and `hostInstanceName`; the parent `titleFontSize/titleColor` overrides and relation-adjusted effective bbox are part of typography truth. Deterministic preview rendering must emit `reports/typography_render_trace.json` proving every rendered text instance used the current spec.
- Read `references/visual-part-coverage-contract.md` for every approved complete-screen design. Every visible structural, semantic, or decorative part must be recorded in `component_visual_parts.json` and mapped to a manifest asset, FairyGUI node, text node, child component, or explicitly approved fallback.
- Read `references/pipeline-stage-timing-contract.md` before an end-to-end run. Initialize timing before Stage 1, start and finish every canonical stage, preserve rework attempts, and output per-stage timing reports before declaring completion.
- Treat `fgui_id_registry.json` as the source of stable package/resource/component IDs. Generate IDs only for new entries; preserve existing IDs on reruns.
- Generate FairyGUI XML only as a draft unless the user has verified it opens in FairyGUI editor.
- Keep image text out of bitmap assets by default. Use FairyGUI text fields and localization keys for real UI text.
- Prefer structured project files: `ui_spec.md`, `visual_design_brief.md`, `design_approval.json`, `uxui_semantic_spec.md`, `component_state_map.json`, `component_visual_parts.json`, `layout_spec.json`, `slice_plan.json`, `asset_manifest.json`, `sheet_plan.md`, `fgui_spec.md`, `pipeline_stage_timings.json`, XML drafts, validation reports, and import checklists.

## Workflow Decision Tree

1. For an end-to-end run, initialize `reports/pipeline_stage_timings.json` before requirement intake and start the `requirement_intake` stage.
2. If the user provides only an idea or gameplay notes, run the requirement sufficiency check and create `ui_spec.md`.
3. When building a complete screen from requirements or design documents, create `visual_design_brief.md`, generate one or more full-screen mockups, finish `design_mockup_generation`, start the waiting-category `design_approval` stage, create a pending `design_approval.json`, present the mockup for confirmation, write a timing snapshot, and stop.
4. Continue only after `scripts/check_design_approval.py` passes for the requested stage. Finish the approval attempt with its real status. The exact approved image becomes the visual source of truth for screen composition and layout.
5. If the user provides an already confirmed design image, require a valid approval record before treating it as approved.
6. After approval, read `references/uxui-semantic-contract.md`, `references/component-reuse-parameterization-contract.md`, and `references/component-instance-configuration-contract.md`, then create `uxui_semantic_spec.md` plus `component_state_map.json`. Every reusable component must declare `reusePlan`; every reusable visible instance must declare `xmlInstanceName`, `controllerPages`, `implementation.configurationMode`, `componentFile`, readable `previewValues`, and runtime bindings. `controller_pages` instances must also declare `implementation.controllerParameters`.
7. Read `references/visual-part-coverage-contract.md` and create `component_visual_parts.json`, inventorying every required icon, frame, title decoration, background, separator, marker, text field, loader, and other visible part without relying on fixed business enums.
8. After semantic/state and visual-part mapping exist, read `references/design-to-layout-contract.md` and create `layout_spec.json`, `slice_plan.json`, and a layout overlay preview or overlay-review risk report before any slicing or XML.
9. Before production asset generation, verify the visual reference gate, approved full-screen design gate, visual-part coverage gate, bitmap provenance plan, asset-isolation plan, production-preview lineage plan, and typography plan; then create `asset_manifest.json`, `sheet_plan.md`, `production_preview_lineage.json`, `typography_spec.json`, and imagegen prompts. For each runtime bitmap, choose exact provided source, exact approved-design crop, or reference reconstruction before generation begins.
10. If the user provides generated sheets or sliced assets, validate them against the manifest, run `validate_asset_isolation.py`, and produce a cut report or correction plan. Every cut must read the exact resource-preview sheet declared by `assetSource.sourceFile`; that file must be registered in `manifest.sheets` and included in `slice_plan.sourceImages`. `reports/cut_report.json` must record one row per sliced asset with the actual source file opened by the slicer, exact crop, output path, derivation mode, source/output SHA-256, and processor-script SHA-256 for deterministic transforms. A rectangular crop cannot claim UI removal, alpha extraction, neighbor cleanup, or hidden-background reconstruction. Freeze the same exact source path, crop/transform mode, source hash, and transform-script hash in `sourceLineage`.
11. Assemble a production preview from the exact staged runtime assets and deterministic typography. The renderer must load `typography_spec.json` and emit `reports/typography_render_trace.json`. Create a pending `production_preview_approval.json`, present the exact preview, and stop for human confirmation. Approval freezes the preview hash and every runtime-asset hash.
12. If the user asks for FairyGUI assembly, create `fgui_spec.md` with semantic component mapping, layout region table, slot table, component ownership table, mandatory Component Reuse Plan, Controller table with `Exported`, Gear mapping table, Instance Configuration with Controller Parameters, Visual Part Coverage, back-to-front Display List columns `Z Layer`/`Occlusion Policy`, transition/relation tables, component hierarchy, binding names, and an XML readiness report.
13. If the user explicitly asks for XML or the current step is XML generation, enter XML Strict Mode. Require passing production-preview lineage and typography-fidelity gates. If any strict input is missing, output `XML生成阻塞报告` and do not emit XML.
14. If the user asks for Unity connection, create binding names, loading notes, package publishing checklist, and smoke-test steps.
15. At the end, finalize and validate stage timing. A completed run requires all 16 canonical stages to be completed or explicitly skipped, and the final handoff must show every stage duration.

## Requirement Sufficiency Gate

Blocking before UX/UI spec:

- game/app type
- target screen
- screen goal
- core user/player operation
- target UI framework if FairyGUI output is expected

Assumable but must be recorded:

- resolution
- orientation
- art style when no visual asset generation is requested
- naming language
- whether text is baked into images
- default asset sizes

Deferred:

- micro-animations
- sound effects
- decorative details
- secondary states
- final balancing values

If blocking information is missing, ask only the minimum necessary questions and stop. If only assumable/deferred information is missing, proceed and record assumptions at the top of `ui_spec.md`.

### Visual Reference Gate

When the current task includes image generation, asset redrawing, style transfer, visual reconstruction, or sheet production, the following become blocking:

- at least one readable reference image
- an explicit reference role and allowed-use declaration
- one primary reference image
- known reference resolution

Do not proceed from text-only requirements to final game art. Without a valid reference image, stop before asset generation and output `视觉参考图阻塞报告`. This gate does not apply to XML-only validation, ID repair, Unity binding generation, or review tasks that do not create visual assets.

### Full-Screen Design Approval Gate

When a complete screen is created from requirements or design documents:

1. create `specs/visual_design_brief.md`
2. generate one or more full-screen design mockups under `generated/design/`
3. create `reports/design_approval.json` with `status=pending`
4. present the exact mockup file to the user and stop
5. after explicit confirmation, bind approval to that exact file with its SHA-256
6. run `scripts/check_design_approval.py` for the requested downstream stage

Without a passing approval gate, do not generate semantic maps, layout specs, production asset plans, sliced resources, FairyGUI assembly plans, or XML. Output `设计稿确认阻塞报告` instead.

A changed or regenerated image invalidates previous approval. Silence, inferred preference, AI self-review, or a request to “continue” without identifying the approved design file does not count as approval.

## Standard Pipeline

0. Initialize timing with `scripts/record_pipeline_timing.py --root UIProduction init`; start and finish every canonical stage as work progresses.
1. Create `ui_spec.md`: screen goal, player flow, region intent, component list, state matrix, art constraints, acceptance criteria.
2. Create `visual_design_brief.md` from requirements, UI/UX documents, and reference images.
3. Generate one or more complete-screen mockups under `generated/design/`.
4. Create `design_approval.json` as pending and stop for explicit human confirmation.
5. Run the approval gate; continue only when the exact design file is approved for the requested stage.
6. Create `uxui_semantic_spec.md` and `component_state_map.json`: visible part inventory, requirement links, component reuse, `reusePlan`, state variants, runtime ownership, per-instance Controller pages, implementation mode, base component file, preview values, runtime bindings, justified structural variants, and mismatch report.
7. Create `component_visual_parts.json`: per-component required visual parts, design evidence, importance, complexity, implementation mode, asset names, XML node names, file scope, and fallback policy.
8. Create `layout_spec.json`, `slice_plan.json`, and `layout_overlay_preview.png` or an overlay-review risk report. Layout objects must reference semantic IDs and the approved design image.
9. Create `asset_manifest.json`: production intent, reference images, resources, sheets, cells, source pixel sizes, display sizes, scale policies, states, pivots, naming, FairyGUI mapping, every asset-backed required visual part, and all required production gates.
10. Create `sheet_plan.md`, `production_preview_lineage.json`, and `typography_spec.json`. Declare exactly how each runtime bitmap reaches the final preview and exactly how every text node is rendered in both preview and XML.
11. Generate or request production image assets: clean environment-only backgrounds, isolated standalone images, transparent sheets, and content-free component skins. Never reuse the complete approved mockup as a runtime background.
12. Slice sheets according to the manifest: output named PNGs, preview contact sheet, `cut_report.json`, and `asset_isolation_review.md`; then run `validate_asset_isolation.py` before assembly.
13. Stage the complete package bundle under `package.outputPath`, then assemble the production preview from those exact staged assets and from `typography_spec.json`.
14. Record pending production-preview approval, present the exact preview, and stop. After explicit approval, freeze preview and runtime-asset hashes with `record_production_preview_approval.py`.
15. Create FairyGUI assembly plan: package, components, display list, semantic component mapping, layout regions, slot grids, component ownership, Component Reuse Plan, Controllers, Gear mappings, Instance Configuration, Visual Part Coverage, transitions, relations, typography mapping, and binding names.
16. Run XML Strict Mode readiness checks, including semantic mapping, component reuse, z-order, bitmap provenance, asset isolation, production-preview lineage, typography fidelity, and visual-part coverage.
17. Generate and validate XML drafts using stable IDs from `fgui_id_registry.json` only if all gates pass.
18. Publish with FairyGUI editor and run Unity smoke tests.
19. Finalize `reports/pipeline_stage_timings.json` / `.md`, validate the timing record, and include total plus per-stage durations in the final handoff.

## XML Strict Mode

XML Strict Mode is mandatory before producing any `package.xml` or component XML.

Strict Mode has two validation profiles:

- `fresh`: for newly generated XML. Enforce 8-character package IDs, registered 2-16 character resource IDs, stable `n{index}_{packageIdLast4}` instance IDs, complete manifest mapping, and no editor-only compatibility attributes unless explicitly justified in `fgui_spec.md`.
- `editor-compatible`: for XML already exported, cleaned, or accepted by FairyGUI editor. Preserve valid editor attributes, extension parameter child nodes, and existing instance IDs; unresolved resources, broken URLs, duplicate IDs, placeholders, and pseudo tags remain hard errors.

Run the readiness gate before XML emission. A passing document review is not enough; `scripts/check_xml_readiness.py` must confirm that strict inputs, stable IDs, resource files, and required `fgui_spec.md` sections are present.

Required inputs:

- embedded `references/fairygui-ai-generation-workflow.md`, read in full for end-to-end pipeline work
- embedded `references/fairygui-xml-parsing-specification.md`, read in full during the current XML task
- `references/fairygui-xml-contract.md`
- `references/xml-strict-generation.md`
- `references/uxui-semantic-contract.md` when the XML is based on requirements plus a design image
- `references/design-to-layout-contract.md` when the XML is based on a design image or reference mockup
- `references/semantic-controller-mapping-contract.md` when components have states, interactions, runtime data, Controllers, or Gears
- `references/component-reuse-parameterization-contract.md` whenever components repeat or multiple candidate XML files share the same visual structure
- `references/component-instance-configuration-contract.md` whenever reusable components have multiple instances, per-instance titles/icons, different Controller pages, or runtime-bound preview data
- `references/display-list-z-order-contract.md` for every component hierarchy and XML displayList
- `references/bitmap-icon-source-contract.md` for small icons, badges, crests, and emblems
- `references/asset-isolation-contract.md` whenever runtime bitmaps are produced from or compared with a complete approved mockup
- `references/production-preview-lineage-contract.md`, `production_preview_lineage.json`, and human `production_preview_approval.json` for every approved complete-screen production asset set
- `references/typography-fidelity-contract.md` and `typography_spec.json` for every final preview or XML containing text
- `references/visual-part-coverage-contract.md` and `component_visual_parts.json` for every approved complete-screen design
- `references/package-resource-path-contract.md` for all package-local file staging, `package.xml path+name`, and component `fileName` work
- `uxui_semantic_spec.md`, `component_state_map.json`, and `component_visual_parts.json` when requirements and a design image are both available
- `visual_design_brief.md`, `design_approval.json`, and the exact approved full-screen design image when the screen was created from requirements/design documents
- a passing design approval gate for `xml_generation`
- `layout_spec.json` and `slice_plan.json` when using a design image or reference mockup as layout source
- `asset_manifest.json` or equivalent manifest
- `fgui_id_registry.json` with stable package IDs, resource IDs, and component instance IDs
- `fgui_spec.md` or equivalent FairyGUI assembly plan containing semantic component mapping, layout region table, slot table, component ownership table, Component Reuse Plan, controller table with `Exported`, gear mapping table, Instance Configuration with Controller Parameters, Visual Part Coverage, transition table, relation/adaptation rules, and a Display List whose rows declare `Asset Name`, `Size`, `Size Source`, `Z Layer`, and `Occlusion Policy`
- real asset file list, or an explicit statement that file existence cannot be checked in this environment
- `references/asset-size-contract.md`
- valid reference-image declarations when the project generated or reconstructed visual assets
- explicit `sourcePixelSize`, `displaySize`, `scalePolicy`, and `renderMode` for every bitmap asset
- `package.outputPath` and exact `packageRelativeFile` for every file-backed package asset
- staged files that exist at `UIProduction/package.outputPath/packageRelativeFile`

If any required input is missing, do not output XML. Output `XML生成阻塞报告` with:

- missing files or fields
- why each item blocks XML generation
- what can still be generated safely
- exact manifest or registry fields that must be added

The report should be generated by `scripts/check_xml_readiness.py` when the project files are accessible. Use `--require-design-approval` whenever the complete-screen design was generated from requirements/design documents, and use `--design-driven` whenever an approved design image is the layout source.

When strict inputs are present:

- Apply the complete XML parsing specification, not a summary.
- For XML generated from a design image, do not emit the main panel XML until semantic mapping, `layout_spec.json`, `slice_plan.json`, the layout region table, slot table, component ownership table, controller table, gear mapping table, and relation/adaptation rules exist.
- Treat same-component/different-state cases as reusable components with different `instanceId` and `stateVariant`, not as unrelated semantic component types.
- For each reusable component, require a `reusePlan`. Prefer a single base component, supported extension override, exported Controller parameter, runtime binding with readable preview fallback, or reusable child components. For a fixed instance page, mark the target Controller `exported="true"` and pass the exact page index through the parent `controller="name,index"`. Allow a variant only when `reusePlan.strategy=variant_allowed` and the XML structure is materially different.
- Reject semantically different instances that all use one unconfigured default component, even when the leaf component's Controllers and Gears are structurally valid.
- Reject separate component XML files whose normalized hierarchy is identical and whose differences are only title, icon, portrait, value, color, size, localization, or selected Controller page.
- Emit `<displayList>` direct children back-to-front. Opaque full-size backgrounds must come first; transparent frames may come later only when explicitly declared and verified.
- Reject production icons made with FairyGUI Graph, SVG, font glyphs, PIL/ImageDraw geometry, Canvas paths, or renamed procedural PNG placeholders. Require approved bitmap provenance in Manifest `assetSource`.
- Reject complete approved mockups used as runtime backgrounds, plain rectangular crops that claim isolation or reconstruction, opaque screenshot rectangles used as portraits/icons, and component skins that contain baked titles, values, states, or reusable child content. For `approved_sheet_slice`, reject undeclared or substituted sheets: `assetSource.sourceFile`, `manifest.sheets`, `slice_plan.sourceImages`, `cut_report.outputs[].sourceFile`, and `sourceLineage.sourceFile` must identify the same exact resource-preview bitmap, and declared crops must match. `cut_report.json` must freeze actual source/output hashes and any deterministic processor script hash. Require `production.requiresAssetIsolation=true`, per-bitmap `assetIsolation`, review evidence, and a passing `validate_asset_isolation.py` report.
- Reject final previews generated independently from the runtime asset set. Require `production.requiresProductionPreviewLineage=true`, an exact production composite, one lineage row per runtime bitmap, source-lineage evidence for exact copy/crop or explicit reference reconstruction, and human approval that freezes preview plus runtime-asset SHA-256 values.
- Reject final preview scripts that hardcode unrelated fonts, sizes, or colors. Require `production.requiresTypographyFidelity=true`, one deterministic `typography_spec.json`, a hash-bound `typography_render_trace.json`, and exact preview/XML equality for declared text attributes and bounds. For reused Button/Label instances, validate effective `titleFontSize`, `titleColor`, title text, host-local bbox after relations, and instance localization rather than checking only the base component text node.
- Editor-preview text must be readable before project runtime localization executes. Prefer literal preview text plus `customData="loc:<key>"`; raw visible `@ui_...` keys block approved-design visual review unless an editor localization plugin is verified.
- Cover package resources, component roots, controllers/actions, displayList, base object attributes, filters, image/loader/text/richtext/graph/list/group, Button/Label/ComboBox/ProgressBar/Slider/ScrollBar/Tree, editor-export compatibility attributes, extension parameter child nodes, Relation, Gear, Transition, enums, branch/high-resolution notes, naming, resource organization, manifest mapping, ID stability, adaptation, localization, and validation rules.
- `src` must be a registered resource ID.
- `fileName` must be the exact package-local `packageRelativeFile`, never the UIProduction-root-relative `asset.file`.
- `package.xml path + name` must resolve to a real resource under the directory containing `package.xml`.
- A referenced Button or Label component may receive external instance parameters through child `<Button .../>` or `<Label .../>` nodes for titles and icons, but the child tag must match the referenced component root `extention`, all attributes must be valid for that extension, and every `ui://` value must resolve.
- Every fresh `<image>` must have an explicit `size` equal to the Manifest `displaySize`.
- The real PNG dimensions must equal Manifest `sourcePixelSize`.
- `pixel_exact` assets require `sourcePixelSize == displaySize`; all other differences require an explicit allowed scale policy.
- Nine-slice assets require a valid `nineSliceGrid` inside `sourcePixelSize`.
- `ui://` URLs must be `ui://{packageId}{resourceId}` with no separator.
- Every fresh Controller must serialize `pages` as `pageId,pageName` pairs and declare an in-range `selected` index. Names-only Controller sequences are invalid even when their comma count is even. Gear `pages` must reference page IDs; Gear `values` group counts must match Gear pages; every `gearLook` state/default must contain all five serialized look fields.
- Every Button extension must retain a valid internal `button` Controller with `up/down/over/disabled` in order, and its `title`/`icon` extension properties must map to actual named children.
- Resource ID length must not be guessed. Prefer exact IDs from `package.xml`, `asset_manifest.json`, or `fgui_id_registry.json`. The default generator may create 5-character lowercase alphanumeric IDs, but existing FairyGUI exports/examples can contain other lowercase alphanumeric lengths.
- Component instance IDs should follow `n{index}_{packageIdLast4}` for newly generated XML and remain stable on reruns. Preserve valid exported IDs during repair unless the user asks to normalize them.
- Never output placeholders such as `包ID`, `资源ID`, `xxxx`, `背景资源ID`, `按钮资源ID`, `PACKAGE_ID`, `RESOURCE_ID`, or unresolved braces.
- Never invent pseudo tags such as `panel`, `sprite`, `container`, or `layer`.
- Generate in deterministic dependency order: `package.xml`, reusable leaf components, composite components, then the main panel. Never generate a parent component before all referenced child resource IDs are registered.
- Write an XML input snapshot to `reports/xml_generation_input_snapshot.json` containing the package name/ID, manifest and registry paths, generation profile, source file hashes or modification times, design resolution, and unresolved-risk list.
- After generating XML, run `scripts/validate_pipeline.py` and `scripts/validate_fgui_xml.py`; write `reports/pipeline_validate_report.json` and `reports/xml_validate_report.json`.
- A validator pass does not make XML final. FairyGUI editor open, publish, and Unity smoke tests remain required.

### Strict Generation Sequence

1. Run `check_design_approval.py --stage xml_generation` when approval is required, then run `check_xml_readiness.py`. Stop on any blocker.
2. Freeze the approved design, approval record, manifest, and registry as the generation input snapshot.
3. Allocate IDs only for new resources/instances; append them to the registry before XML references them.
4. Stage every resource under `package.outputPath/packageRelativeFile` and validate the complete package bundle.
5. Generate `package.xml` from package-local paths and validate `path + name` against real files.
6. Generate reusable leaf components and parameterized child components first.
7. Generate base composite components; generate a variant only after `validate_component_reuse.py` accepts its structural justification.
8. Materialize every required part from `component_visual_parts.json`, then generate the main screen.
9. Materialize every `component_state_map.visualInstances` entry in the parent XML and validate its base component file, default Controller pages, extension parameters, preview text, runtime-binding declaration, and any justified variant.
10. Validate exact component `fileName` paths; basename-only matches are forbidden in `fresh` mode.
11. Run structural and cross-source validation in the selected profile, including component reuse, display-list z-order, bitmap provenance, asset isolation, and visual-part coverage.
12. Produce the import checklist and mark XML as `draft_unverified` until FairyGUI editor accepts it.
13. After editor cleanup/export, rerun validation using `--mode editor-compatible` and record any accepted compatibility differences.

### Strict Failure Policy

- Never partially emit a main panel XML when readiness is blocked.
- A failed leaf component may block only its dependent parent components; unrelated components may still be generated if their dependency set is complete.
- Do not rewrite or renumber existing registry IDs to repair one failed component.
- Do not silently downgrade errors. Any accepted exception must be recorded in `fgui_spec.md` and the validation report.

## Storage Boundary

Keep reusable pipeline instructions in this skill:

- workflow stages and blocking gates
- generic schemas for `uxui_semantic_spec.md`, `component_state_map.json`, `layout_spec.json`, `slice_plan.json`, manifest, registry, and XML readiness
- FairyGUI XML rules and validators
- report templates and validation scripts

Keep project-specific production data in the project's `UIProduction` tree:

- concrete screen specs and design assumptions
- requirement-to-visual semantic maps and component state maps
- design-image-derived regions, slots, object boxes, and overlay reviews
- slice plans with exact crop boxes and output asset names
- `asset_manifest.json`, `fgui_id_registry.json`, `fgui_spec.md`, generated XML drafts, and validation reports

Do not write project names such as `store_main`, coordinates such as `815,514,439,264`, package IDs, or concrete component IDs into the reusable skill. Put those in `D:\Game2\Docs\UIProduction\...` or the equivalent project directory.

## Required Output Bundle

Use this directory shape unless the user gives an existing project layout:

```text
UIProduction/
├── references/
│   └── <primary_reference_image>
├── specs/
│   ├── ui_spec.md
│   ├── visual_design_brief.md
│   ├── uxui_semantic_spec.md
│   ├── component_state_map.json
│   ├── component_visual_parts.json
│   ├── layout_spec.json
│   ├── slice_plan.json
│   └── fgui_spec.md
├── manifests/
│   ├── asset_manifest.json
│   └── fgui_id_registry.json
├── generated/
│   ├── design/
│   │   ├── screen_design_draft_v1.png
│   │   └── screen_design_final.png
│   ├── sheets/
│   ├── sliced/
│   └── preview/
├── fgui_xml/
│   └── <package_name>/
│       ├── package.xml
│       ├── <component>.xml
│       └── art/
│           └── <package_resource>.png
└── reports/
    ├── design_draft_review.md
    ├── design_approval.json
    ├── design_gate_report.json
    ├── design_gate_blocking_report.md
    ├── semantic_layout_consistency_report.md
    ├── semantic_controller_mapping_report.json
    ├── semantic_controller_mapping_report.md
    ├── component_reuse_report.json
    ├── component_reuse_report.md
    ├── display_list_z_order_report.json
    ├── display_list_z_order_report.md
    ├── bitmap_asset_provenance_report.json
    ├── bitmap_asset_provenance_report.md
    ├── asset_isolation_report.json
    ├── asset_isolation_report.md
    ├── asset_isolation_review.md
    ├── production_preview_approval.json
    ├── production_preview_lineage_report.json
    ├── production_preview_lineage_report.md
    ├── typography_fidelity_report.json
    ├── typography_fidelity_report.md
    ├── visual_part_coverage_report.json
    ├── visual_part_coverage_report.md
    ├── pipeline_stage_timings.json
    ├── pipeline_stage_timings.md
    ├── cut_report.json
    ├── xml_readiness_report.json
    ├── xml_blocking_report.md
    ├── xml_generation_input_snapshot.json
    ├── pipeline_validate_report.json
    ├── xml_validate_report.json
    ├── xml_editor_compatible_report.json
    └── fgui_import_checklist.md
```

## Reference Loading

Load only the relevant reference files for the current step:

- `references/fairygui-ai-generation-workflow.md`: complete embedded original workflow document; do not summarize or skip chapters.
- `references/fairygui-xml-parsing-specification.md`: complete embedded original XML parsing specification; mandatory for XML work.
- `references/embedded-docs-manifest.json`: portable integrity metadata for both embedded originals.
- `scripts/verify_embedded_docs.py`: exact byte-length, required-section, tail-record, and external-dependency validator.
- `references/pipeline.md`: skill-enhanced workflow, checkpoints, and production rules.
- `references/uxui-semantic-contract.md`: requirement-plus-design-image semantic/state mapping workflow.
- `references/manifest-contract.md`: manifest and ID registry work.
- `references/visual-reference-contract.md`: mandatory reference-image gate for visual resource production.
- `references/design-mockup-approval-contract.md`: full-screen mockup generation, explicit human approval, approval scope, and invalidation rules.
- `references/asset-size-contract.md`: source pixel, display size, scale-policy, layout, and XML consistency rules.
- `references/semantic-controller-mapping-contract.md`: requirement/design evidence, state ownership, Controller pages, Gear mappings, layout inheritance, external Button/Label instance parameter semantics, and XML implementation rules.
- `references/component-reuse-parameterization-contract.md`: reuse-first component design, base files, parameterizable fields, reusable child components, justified variants, and duplicate-structure blocking.
- `scripts/validate_component_reuse.py`: validates `reusePlan`, Component Reuse Plan, external parameter declarations, composite-child references, and normalized XML structure.
- `references/component-instance-configuration-contract.md`: per-instance defaults, extension overrides, exported Controller parameters, runtime bindings, justified structural variants, readable preview text, and visual-review rules for reusable components.
- `scripts/validate_semantic_controller_mapping.py`: executable cross-source validator for `ui_spec.md`, `uxui_semantic_spec.md`, `component_state_map.json`, `layout_spec.json`, `fgui_spec.md`, Controller exports/parameters, per-instance configuration, and optional component XML.
- `references/display-list-z-order-contract.md`: back-to-front Display List planning, opaque-background placement, transparent-frame classification, and overlay rules.
- `scripts/validate_display_list_z_order.py`: validates fgui_spec order/layers, layout z fields, and XML direct-child order.
- `references/bitmap-icon-source-contract.md`: approved bitmap provenance and no-procedural-icon rules.
- `scripts/validate_bitmap_asset_provenance.py`: validates icon `assetSource` evidence and scans production scripts for procedural geometry.
- `references/asset-isolation-contract.md`: clean-background, transparent-subject/icon, no-neighbor-pixel, no-baked-dynamic-content, and full-screen-reference-only rules.
- `scripts/validate_asset_isolation.py`: validates Manifest isolation declarations, slice-plan claims, crop scripts, runtime outputs, alpha heuristics, and review evidence.
- `references/production-preview-lineage-contract.md`: two-stage approval, exact runtime-asset preview composition, hash freezing, and no-regeneration-after-approval rules.
- `scripts/record_production_preview_approval.py`: creates pending or human-approved records bound to the exact production preview and runtime asset hashes.
- `scripts/validate_production_preview_lineage.py`: validates preview/Manifest/runtime file identity, renderer usage, approvals, and frozen hashes.
- `references/typography-fidelity-contract.md`: deterministic typography source, supported FairyGUI text attributes, preview/XML equality, and human review rules.
- `scripts/validate_typography_fidelity.py`: validates typography spec, renderer linkage, text styles, bounds, localization mapping, and XML attributes.
- `references/visual-part-coverage-contract.md`: complete-screen visible-part inventory and no-silent-omission rules.
- `scripts/validate_visual_part_coverage.py`: validates `component_visual_parts.json` against Manifest, `fgui_spec.md`, Registry, and optional XML.
- `references/pipeline-stage-timing-contract.md`: canonical stage IDs, active/waiting/external categories, rework-attempt preservation, completion rules, and final timing-report requirements.
- `scripts/record_pipeline_timing.py`: initializes, starts, finishes, skips, snapshots, finalizes, validates, and command-wraps per-stage timing.
- `references/package-resource-path-contract.md`: UIProduction-root paths versus package-local paths, atomic package staging, and exact resource resolution.
- `references/design-to-layout-contract.md`: design image to layout/slice/XML gated workflow.
- `references/fairygui-xml-contract.md`: concise XML gate.
- `references/fairygui-xml-parsing-spec.md`: local alias/index that points only to the embedded `references/fairygui-xml-parsing-specification.md`; it must not depend on an external path.
- `references/xml-strict-generation.md`: step-by-step XML generation and self-check procedure.
- `references/output-templates.md`: standard documents and reports.

## Validation Script

After copying this skill to another computer, and before using its production rules, verify the two embedded complete documents:

```bash
python scripts/verify_embedded_docs.py
```

Any failure blocks pipeline and XML work until the embedded files and `references/embedded-docs-manifest.json` agree.

Before any downstream stage of a generated full-screen design, run the approval gate, for example:

```bash
python scripts/check_design_approval.py --root UIProduction --stage semantic_analysis --out UIProduction/reports/design_gate_report.json --report-md UIProduction/reports/design_gate_blocking_report.md
```

Before XML generation, validate semantic Controller/Gear mapping and then run readiness:

```bash
python scripts/validate_semantic_controller_mapping.py --root UIProduction --stage xml_generation --out UIProduction/reports/semantic_controller_mapping_report.json --report-md UIProduction/reports/semantic_controller_mapping_report.md
python scripts/validate_component_reuse.py --root UIProduction --stage xml_generation --out UIProduction/reports/component_reuse_report.json --report-md UIProduction/reports/component_reuse_report.md
python scripts/validate_display_list_z_order.py --root UIProduction --stage xml_generation --out UIProduction/reports/display_list_z_order_report.json --report-md UIProduction/reports/display_list_z_order_report.md
python scripts/validate_bitmap_asset_provenance.py --root UIProduction --stage xml_generation --out UIProduction/reports/bitmap_asset_provenance_report.json --report-md UIProduction/reports/bitmap_asset_provenance_report.md
python scripts/validate_asset_isolation.py --root UIProduction --stage xml_generation --xml-dir UIProduction/fgui_xml/<package_name> --out UIProduction/reports/asset_isolation_report.json --report-md UIProduction/reports/asset_isolation_report.md
python scripts/validate_production_preview_lineage.py --root UIProduction --stage xml_generation --out UIProduction/reports/production_preview_lineage_report.json --report-md UIProduction/reports/production_preview_lineage_report.md
python scripts/validate_typography_fidelity.py --root UIProduction --stage xml_generation --xml-dir UIProduction/fgui_xml/<package_name> --out UIProduction/reports/typography_fidelity_report.json --report-md UIProduction/reports/typography_fidelity_report.md
python scripts/validate_visual_part_coverage.py --root UIProduction --stage xml_generation --out UIProduction/reports/visual_part_coverage_report.json --report-md UIProduction/reports/visual_part_coverage_report.md
python scripts/check_xml_readiness.py --root UIProduction --profile fresh --require-design-approval --resource-generation --design-driven --out UIProduction/reports/xml_readiness_report.json --report-md UIProduction/reports/xml_blocking_report.md --snapshot-out UIProduction/reports/xml_generation_input_snapshot.json
```

Omit `--design-driven` only when no design image, screenshot, or reference mockup is used for layout. Omit `--resource-generation` only for XML-only validation, ID repair, binding generation, or projects whose visual assets were not generated/redrawn by this pipeline.

When a manifest or ID registry exists, run:

```bash
python scripts/validate_pipeline.py --root UIProduction --out UIProduction/reports/pipeline_validate_report.json
```

When newly generated XML files exist, run:

```bash
python scripts/validate_fgui_xml.py --xml-dir UIProduction/fgui_xml/<package_name> --manifest UIProduction/manifests/asset_manifest.json --registry UIProduction/manifests/fgui_id_registry.json --mode fresh --out UIProduction/reports/xml_validate_report.json
```

For XML already accepted, cleaned, or exported by FairyGUI editor, rerun with:

```bash
python scripts/validate_fgui_xml.py --xml-dir UIProduction/fgui_xml/<package_name> --manifest UIProduction/manifests/asset_manifest.json --registry UIProduction/manifests/fgui_id_registry.json --mode editor-compatible --out UIProduction/reports/xml_editor_compatible_report.json
```

## Completion Checklist

Before calling the pipeline complete, confirm:

- `scripts/record_pipeline_timing.py --root UIProduction finalize --status completed` and `validate` pass; both timing reports exist and the final handoff includes every stage duration.
- `scripts/verify_embedded_docs.py` confirms both embedded complete source documents are intact.
- Blocking requirements were resolved or explicitly asked.
- Requirement-to-visual semantic mapping exists before layout and XML when a design image is used.
- Requirement states, semantic ownership, layout state fields, `fgui_spec.md` Controllers/Gears/Instance Configuration, and existing XML pass `validate_semantic_controller_mapping.py` for the requested stage.
- Reuse plans, parameterizable fields, exported Controller parameters, child-component references, Component Reuse Plan rows, and XML structural signatures pass `validate_component_reuse.py`.
- Display List z-order passes `validate_display_list_z_order.py`; opaque backgrounds precede content and intentional frames/overlays are explicitly classified.
- Every icon has approved bitmap provenance and `validate_bitmap_asset_provenance.py` finds no procedural vector-like generator.
- Every production bitmap has the required `assetIsolation` declaration; clean backgrounds contain no UI/characters, isolated portraits/icons have valid alpha and no neighboring pixels, skins contain no baked dynamic content, and `validate_asset_isolation.py` plus `asset_isolation_review.md` pass.
- The final production preview is assembled from exact staged runtime files, every asset hash is frozen by human approval, and `validate_production_preview_lineage.py` passes.
- The final preview and XML share one approved `typography_spec.json`; font identity, size, color, alignment, spacing, stroke/shadow, bounds, preview text, and localization mapping pass `validate_typography_fidelity.py`. Reused Button/Label instances with distinct title styles have host-target rows and matching effective parent overrides/bounds.
- Every approved-design visible part is recorded in `component_visual_parts.json`; asset-backed parts exist in Manifest, required XML nodes exist, and detailed Graph downgrades have explicit human approval.
- Same-component/different-state visual cases are represented by one base component plus state/instance configuration; separate variants exist only for documented and machine-verifiable structural differences.
- Every reusable component has a valid `reusePlan` and matching Component Reuse Plan row; every reusable visual instance has a unique `xmlInstanceName`, explicit implementation mode, base component file, Controller pages where applicable, readable preview values, and runtime bindings.
- FairyGUI preview contains no unintended duplicate default portraits/icons/titles, raw localization keys, blank controls, or white placeholder blocks.
- Visual resource production used at least one valid primary reference image with an explicit role.
- Full-screen design generation produced `visual_design_brief.md`, an exact approved design image, and a passing human approval gate before any downstream decomposition or production.
- Manifest, sheet plan, sliced asset names, and FairyGUI resource references agree; every `approved_sheet_slice` uses the exact registered resource-preview sheet, and `assetSource.sourceFile`, `slice_plan.sourceImages`, `cut_report.outputs[].sourceFile/crop/hashes`, and `sourceLineage.sourceFile/crop` agree byte-source-for-byte-source.
- Every file-backed asset has `packageRelativeFile`, and `asset.file == package.outputPath/packageRelativeFile`.
- Every `package.xml path+name` and component `fileName` resolves exactly inside the staged package directory.
- Actual image pixels, Manifest `sourcePixelSize`, Manifest `displaySize`, layout bounds, and XML image sizes agree under the declared scale policy.
- IDs are stable through `fgui_id_registry.json`.
- XML readiness gate passes with no blockers.
- All Controllers use `pageId,pageName` pairs with valid defaults; all Gear pages resolve to those IDs; every `gearLook` tuple has five fields; Button extension internals follow the `button/title/icon` contract.
- Pipeline, manifest/registry, and XML cross-source validations pass in the correct profile.
- XML generation input snapshot exists and records unresolved risks.
- XML was opened and published by FairyGUI editor before being called final.
- The user has a FairyGUI editor import checklist and Unity smoke-test steps.
