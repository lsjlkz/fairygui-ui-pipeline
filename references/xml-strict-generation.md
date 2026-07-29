# XML Strict Generation Procedure

Use this procedure for any FairyGUI `package.xml` or component XML generation, review, repair, or validation.

This file does not replace the user's full `fairygui-xml-parsing-specification.md`. It is a checklist that forces the full specification to be applied.

## Strict Mode Profiles

Choose exactly one profile before reading or emitting XML.

### `fresh`

Use for newly generated XML. Enforce exact 8-character package IDs, registered 2-16 character resource IDs, stable `n{index}_{packageIdLast4}` instance IDs, complete manifest mapping, and no undocumented editor-only compatibility output.

### `editor-compatible`

Use only for XML already opened, cleaned, accepted, or exported by FairyGUI editor. Preserve valid existing IDs, editor attributes, and extension parameter child nodes. Instance-ID convention differences become warnings, but placeholders, duplicate IDs, broken URLs, unregistered resources, pseudo tags, and malformed XML remain hard errors.

Do not use `editor-compatible` merely to make newly generated XML pass.

## 1. Mandatory Reading Order

Before producing XML-related output, read:

1. `references/fairygui-ai-generation-workflow.md` in full for the end-to-end production rules.
2. `references/fairygui-xml-parsing-specification.md` in full for all XML structures, attributes, mappings, compatibility rules, and validation rules.
3. `references/fairygui-xml-parsing-spec.md` as the local index only; it does not replace the two full documents.
4. `references/fairygui-xml-contract.md`.
5. `references/manifest-contract.md` when manifest or registry files are involved.
6. `references/visual-reference-contract.md` when visual assets were generated, redrawn, or reconstructed.
7. `references/design-mockup-approval-contract.md` when a complete screen design was generated from requirements or design documents.
8. `references/semantic-controller-mapping-contract.md` whenever states, interactions, Controllers, Gears, or runtime ownership exist.
9. `references/component-reuse-parameterization-contract.md` whenever components repeat or candidate XML files share a hierarchy.
10. `references/component-instance-configuration-contract.md` whenever a reusable component has multiple semantic instances or per-instance data.
11. `references/display-list-z-order-contract.md` for every component hierarchy and XML displayList.
12. `references/bitmap-icon-source-contract.md` for icon-like visual assets.
13. `references/asset-isolation-contract.md` for every runtime bitmap produced from or compared with an approved full-screen mockup.
14. `references/production-preview-lineage-contract.md` for exact staged-asset preview composition and the second human approval.
15. `references/typography-fidelity-contract.md` for deterministic preview/XML text rendering.
16. `references/visual-part-coverage-contract.md` for every approved complete-screen design.
17. `references/asset-size-contract.md` for every bitmap resource.
18. `references/package-resource-path-contract.md` before package staging or XML generation.
19. The current `ui_spec.md`, `visual_design_brief.md`, `design_approval.json`, `uxui_semantic_spec.md`, `component_state_map.json`, `component_visual_parts.json`, `layout_spec.json`, `production_preview_lineage.json`, `typography_spec.json`, `fgui_spec.md`, `asset_manifest.json`, and `fgui_id_registry.json` as applicable.

If either embedded complete source document cannot be read in the current task, or `scripts/verify_embedded_docs.py` reports a failure, do not generate XML.

Before XML generation, verify the embedded complete documents and then run the executable readiness gate:

```bash
python scripts/verify_embedded_docs.py
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

Omit `--require-design-approval` only when the complete-screen design was not generated from requirements/design documents and no approval-controlled design is declared. Omit `--design-driven` only when no design image is used for layout. Omit `--resource-generation` only when the current pipeline did not generate, redraw, restyle, or reconstruct visual assets. A non-zero exit code blocks XML generation.

## 2. XML Readiness Gate

Generate XML only when all of these are known:

- package directory name
- package ID
- package resource table
- component XML filenames
- all image/sound/movieclip/font/atlas/misc resource names and paths
- all resource IDs used by `src`, `url`, `icon`, `sound`, `defaultItem`, `dropdown`, and gear values
- component tree and display order
- coordinates and sizes
- a valid primary reference-image declaration when visual resources were produced
- explicit human approval of the exact full-screen design file when the screen design was generated by the pipeline
- an approval SHA-256 that still matches the current design bytes
- approval scope containing `xml_generation`
- every bitmap's actual pixels, `sourcePixelSize`, `displaySize`, `scalePolicy`, and `renderMode`
- every file-backed resource's exact `packageRelativeFile`
- `asset.file == package.outputPath/packageRelativeFile`
- controller page definitions derived from requirement-defined and design-visible discrete states
- every reusable component's `reusePlan`, base component file, extension, parameterizable fields, reusable child files, and allowed structural-variant reasons
- every visual instance's `xmlInstanceName`, implementation mode, base component file, Controller pages, `controllerParameters` when externally passed, readable preview values, runtime bindings, and justified variant data when applicable
- every Display List row's `Z Layer` and `Occlusion Policy`, with opaque backgrounds first
- every icon asset's approved bitmap `assetSource`
- `production.requiresAssetIsolation=true` for complete-screen projects, every bitmap's `assetIsolation` declaration, and passing automated plus human isolation review
- `production.requiresProductionPreviewLineage=true`, exact runtime-file preview usage, one `sourceLineage` entry per runtime bitmap, valid exact-copy/crop or reconstruction evidence, passing human production-preview approval, and unchanged source/transform/preview/runtime SHA-256 values
- `production.requiresTypographyFidelity=true`, one approved typography spec, deterministic preview rendering with a current hash-bound render trace, and exact XML text attributes/bounds
- every approved-design visual part's importance, complexity, implementation mode, manifest asset or XML node, file scope, and fallback policy
- business state owner, visual state owner, and dynamic-data owner
- relation targets
- gear controller/page/value mapping for every semantic visual difference
- transition item types and values
- text/localization strategy
- stable instance IDs or permission to allocate them
- editor-cleaned compatibility mode status: whether the XML is fresh AI output, existing FairyGUI export, or XML that has already passed editor cleanup

If any item is missing, output `XML生成阻塞报告` instead of XML.

The automated readiness gate additionally verifies:

- the complete XML specification exists and is not merely a small bridge file
- the manifest package maps to an exact 8-character package ID
- stable resource IDs are present and unique
- an instance ID registry exists
- required `fgui_spec.md` sections exist
- requirement State Matrix, semantic components/state groups/visualInstances, layout state ownership, Controllers, Gear Mapping, and Instance Configuration tables pass `validate_semantic_controller_mapping.py`
- reusable components, parameterizable fields, exported Controller parameters, composite children, Component Reuse Plan rows, and XML structural signatures pass `validate_component_reuse.py`
- Display List back-to-front ordering passes `validate_display_list_z_order.py`
- icon provenance and production-script audit pass `validate_bitmap_asset_provenance.py`
- resource isolation passes `validate_asset_isolation.py`: no complete mockup used as runtime background, no plain-crop isolation claims, no opaque screenshot portraits/icons, and no baked dynamic content in skins
- production preview lineage passes `validate_production_preview_lineage.py`: every runtime bitmap is mapped to exact preview usage, declares exact approved/provided source or justified reference reconstruction, and all source/transform/human-approved hashes remain unchanged
- typography fidelity passes `validate_typography_fidelity.py`: preview renderer loads the typography spec, emits a matching per-instance render trace, and XML matches all declared text attributes, bounds, preview text, and localization mapping
- reusable instances with different semantics do not all fall back to one default component
- content-only differences do not produce separate XML files
- justified structural variants have non-identical XML signatures and matching default Controller pages
- external instance parameters match the semantic reuse plan
- required icons, frames, title decorations, backgrounds, separators, markers, and text parts declared by the project are covered by Manifest and XML
- detailed visual parts are not silently degraded to Graph without explicit human approval
- editor-preview text does not expose unresolved localization keys
- design-driven semantic, layout, slice, and overlay artifacts exist when required
- valid primary reference images exist and their declared resolution equals real pixels when resource generation is enabled
- real files referenced by the manifest exist
- every staged resource exists under `package.outputPath/packageRelativeFile`
- actual image pixels equal `sourcePixelSize`
- layout image bounds equal Manifest `displaySize`
- fresh XML image sizes equal Manifest `displaySize`
- skipping image metadata is a blocker in `fresh` mode

## 3. Spec Coverage Checklist

Before outputting XML, verify these chapters from the full specification:

| Spec Section | Required Application |
|---|---|
| 1. 文件结构和URL | output directory and `ui://{packageId}{resourceId}` references |
| 2. package.xml | root node, resource node types, `id/name/path/exported` |
| 3. component XML | root `component`, `controller`, `action`, `displayList` |
| 4. base objects | common attributes, filters, image, loader, text, richtext, graph, list, group |
| 5. extensions | Button, Label, ComboBox, ProgressBar, Slider, ScrollBar, Tree, plus external instance parameter overrides and target `extention` matching |
| 6. Relation | `relation target`, `sidePair`, parent target handling |
| 7. Gear | gear tags, controller/page/value/default mapping, tween child |
| 8. Transition | transition attributes, item attributes, action type enum |
| 9. enumerations | allowed values for object/layout/fill/button/group/etc. |
| 10. mechanisms | branch/high-resolution/string/version/extension compatibility notes |
| 11. examples | generated shape should resemble valid examples, not pseudo XML |
| 13. naming | package/component/object/controller naming and ID stability |
| 14. resources | resource directory and image naming rules |
| 15. AI constraints | UTF-8, Windows CRLF when writing final files, 2-space indent, attribute order |
| 16. manifest mapping | manifest fields map to XML fields exactly |
| 17. ID registry | reuse stable IDs, never regenerate all IDs on rerun |
| 18. automation boundary | call XML a draft until FairyGUI editor confirms it |
| 19. validation | generate `xml_validate_report.json` |
| 20. adaptation | Relation strategy, no blind stretching |
| 21. localization | use text/richtext and localization keys, avoid baked text |
| 22-23. pipeline | place outputs in production directory and keep editor publish as final step |

For XML reviews, include a concise version of this checklist in the review result. For XML generation, use it internally and mention only blockers/warnings unless the user asks for full reasoning.

## 4. Resource ID Rules

Do not infer resource IDs from filenames or display names.

Priority order:

1. existing `package.xml`
2. `fgui_id_registry.json`
3. `asset_manifest.json`
4. explicit user-provided resource table
5. newly allocated IDs, only when the user requested generation and the registry can be updated

The default generator may create 5-character lowercase alphanumeric resource IDs. However, imported FairyGUI examples can contain other lowercase alphanumeric resource ID lengths. Therefore:

- references must resolve to an actual registered ID
- validators should prefer registry/package lookup over fixed length checks
- generated IDs should follow the project generator unless the existing project proves another format
- package IDs must always be exactly 8 lowercase alphanumeric characters
- generated resource IDs must be 2-16 lowercase alphanumeric characters
- register new IDs before any XML references them
- append new instance IDs after retained generated indices; never renumber existing objects
- move deleted IDs to `retired` instead of silently reusing them

## 5. Generation Input Snapshot

Before allocating IDs or writing XML, create `reports/xml_generation_input_snapshot.json` containing:

- selected profile: `fresh` or `editor-compatible`
- package name and package ID
- design resolution
- paths to manifest, registry, `fgui_spec.md`, `visual_design_brief.md`, `design_approval.json`, the exact approved design image, production-preview lineage/approval, typography spec/render trace, design-driven semantic/layout sources, reference images, and generated asset files
- hashes when available, otherwise modification times
- unresolved risks and accepted exceptions
- status `frozen_for_generation`

If any frozen source changes during generation, stop, regenerate the snapshot, rerun readiness, and restart the affected dependency scope.

## 6. Dependency-Ordered Generation

Generate in this order:

1. update and freeze `fgui_id_registry.json`
2. stage every file-backed resource under `package.outputPath/packageRelativeFile`
3. validate the complete package-local resource bundle
4. generate `package.xml` from `packageRelativeFile`
5. validate `package.xml path + name` against the real package directory
6. generate reusable leaf components with no component dependencies
7. generate reusable parameterized child components and export any Controller intended for parent-instance configuration
8. generate base composite components after their children exist
9. generate only structurally justified variants accepted by `validate_component_reuse.py`
10. validate every staged bitmap with `validate_asset_isolation.py`; reject full-screen mockup backgrounds, contaminated crops, missing alpha, and baked dynamic content
11. validate every runtime bitmap's `sourceLineage`: exact provided/approved source when possible, deterministic transform evidence when necessary, or justified reference reconstruction
12. assemble the exact production preview from staged assets and `typography_spec.json`, emit `typography_render_trace.json`, obtain human approval, and freeze source/transform/preview/runtime hashes
13. materialize every required visual part from `component_visual_parts.json`, using approved and isolated bitmaps for icons
14. generate the main screen last, with direct children ordered back-to-front, and materialize every visual instance
15. validate exact component paths, reuse plans, Controller parameters, z-order, source/preview asset lineage, typography spec/trace/XML attributes and bounds, required visual nodes, and runtime bindings
16. generate validation reports and the FairyGUI import checklist

A parent component may not reference a child whose resource ID is absent from both `package.xml` and the registry. A failed component blocks its dependants, but does not require unrelated IDs or components to be regenerated. Never emit a partially wired main panel.

## 7. Editor Compatibility Rules

When reviewing or repairing XML from `GameUI/assets` that has already been accepted or cleaned by FairyGUI editor:

- Preserve editor-compatible attributes such as `designImageOffsetY`, `aspect`, `group`, `controller`, `advanced`, `anchor`, `clearOnPublish`, `autoClearText`, `autoPlay`, and `autoPlayRepeat`.
- Preserve extension parameter child nodes under component instances, for example `<component ...><Button title="..." icon="ui://..."/></component>` and `<component ...><Label title="..." icon="ui://..."/></component>`.
- Do not rewrite these compatibility forms into a different structure unless the editor reports an error or the user explicitly asks to normalize them.
- For fresh AI-generated XML, prefer the core spec attributes and only emit compatibility attributes when the source spec, existing export, or user request requires them.

## 8. Blocking Report Template

```md
# XML生成阻塞报告

## 不能生成 XML 的原因
- ...

## 缺失的规范或输入
- ...

## 需要补齐的 manifest/registry 字段
- ...

## 当前可以安全输出
- fgui_spec.md 修正建议
- asset_manifest.json 修正建议
- fgui_id_registry.json 草案
- FairyGUI 编辑器拼装计划
```

## 9. Generation Rules

- Preserve existing IDs from the registry.
- Append new instance IDs instead of renumbering existing display objects.
- Use `src` for image/component resource IDs.
- Use `fileName` for the exact `packageRelativeFile`, not the UIProduction-root-relative `file` path.
- Build `package.xml path + name` from `packageRelativeFile` and require the represented path to exist under the package directory.
- Never accept basename-only resource matching in `fresh` mode.
- Every fresh image node must have explicit `size` equal to Manifest `displaySize`.
- Actual image pixels must equal `sourcePixelSize`.
- `pixel_exact` requires source and display sizes to match; every other difference requires an explicit permitted scale policy.
- Never infer display size from the PNG or infer source pixels from the layout.
- Use `pkg` only for cross-package references.
- Use `url`, `icon`, `sound`, `dropdown`, and `defaultItem` only with resolvable `ui://` URLs.
- Resolve every controller, page, relation target, gear target, transition target, and list item before emission.
- Serialize every Controller `pages` attribute as exact `pageId,pageName` pairs, for example `0,up,1,down,2,over,3,disabled`; never emit a names-only sequence such as `up,down,over,disabled`. Fresh generated Controllers must explicitly declare a valid `selected` page index.
- Gear `pages` values must reference the Controller page IDs, not page names. Every `values` group count must equal the Gear page count. Each `gearLook` state and `default` must use the five-field FairyGUI serialization; four-field look tuples are forbidden.
- A Button extension must have the internal `button` Controller with pages `up/down/over/disabled` in that order, plus valid `title` and `icon` children when those extension properties are used. Button enum values must use the XML spelling accepted by the embedded specification or a verified editor export.
- For every component-instance extension parameter child node, resolve the target component XML, require the child tag to equal the target root `extention`, validate allowed attributes, and resolve all `ui://` values.
- Materialize every `component_state_map.visualInstances` record. A reusable component with different role/state/title/icon/preview data cannot silently use `static_default` for all instances.
- Require `reusePlan` for every reusable semantic component. Prefer one base component plus external Button/Label parameters, Controller pages, runtime bindings, or reusable child components.
- Do not create variants solely for title, icon, portrait, number, color, size, localization, or selected-page differences.
- For `controller_pages`, require `reusePlan.parameterizableFields` to include `controller.<name>`, target `controller@exported=true`, semantic `controllerParameters`, and exact parent `controller="name,pageIndex"`.
- For `variant_component`, require `reusePlan.strategy=variant_allowed`, a valid `variantJustification`, and a normalized XML structure different from the base and sibling variants.
- For `composite_component`, require the base XML to reference every declared reusable child component.
- Materialize every required visible part in `component_visual_parts.json`; omission of a small icon, frame, title decoration, separator, background, marker, or required text is a hard error.
- Emit displayList children back-to-front and block any opaque full-size background that appears after content.
- Require icon assets to come from approved design/sheet slices, provided bitmaps, existing package bitmaps, or reference-driven image generation. Programmatic vector-like icon drawing is forbidden.
- Require complete-screen projects to set `requiresAssetIsolation=true`; every bitmap must declare an isolation role and review evidence. Do not use the approved full-screen design as a runtime background or universal crop source. A plain crop cannot claim UI removal, alpha extraction, neighbor cleanup, baked-text removal, or hidden-pixel reconstruction.
- Require `requiresProductionPreviewLineage=true`; every runtime bitmap must declare exact approved/provided source or justified reference reconstruction plus deterministic derivation evidence. The final preview must use exact staged runtime files and a human approval bound to preview plus asset hashes. Regeneration after approval is forbidden until the approval is superseded.
- Require `requiresTypographyFidelity=true`; image-model lettering is reference-only, preview/XML text must come from one approved typography spec, and deterministic preview rendering must emit a current hash-bound per-instance render trace.
- Asset-backed parts must resolve to the declared Manifest asset and registered package resource.
- Detailed visual parts may use Graph only after explicit human approval recorded in the coverage file.
- For a justified `variant_component`, require the registered target XML's selected Controller pages to match the instance declaration.
- For `runtime_binding`, provide readable preview fallback values and record the runtime fields.
- Keep editor-preview text readable; store localization identity separately instead of displaying raw `@ui_...` keys unless editor resolution is verified.
- Do not output pseudo tags, placeholders, unresolved braces, or guessed resource IDs.
- Do not silently downgrade errors. Accepted exceptions must appear in `fgui_spec.md` and the validation report.
- Do not generate an XML Controller or Gear plan that cannot be traced back to requirement/design evidence and `component_state_map.json`.
- Do not claim XML is final until FairyGUI editor opens and publishes it successfully.

## 10. Post-Generation Validation

Run the pipeline validator:

```bash
python scripts/validate_pipeline.py --root UIProduction --out UIProduction/reports/pipeline_validate_report.json
```

For newly generated XML:

```bash
python scripts/validate_fgui_xml.py --xml-dir UIProduction/fgui_xml/<package_name> --manifest UIProduction/manifests/asset_manifest.json --registry UIProduction/manifests/fgui_id_registry.json --mode fresh --out UIProduction/reports/xml_validate_report.json
```

After FairyGUI editor cleanup or export:

```bash
python scripts/validate_fgui_xml.py --xml-dir UIProduction/fgui_xml/<package_name> --manifest UIProduction/manifests/asset_manifest.json --registry UIProduction/manifests/fgui_id_registry.json --mode editor-compatible --out UIProduction/reports/xml_editor_compatible_report.json
```

Any hard error prevents the XML from being called ready for import. A validator result that does not check exact package-local resource paths is insufficient.

## 11. XML Status Lifecycle

Use these states:

- `blocked`: readiness gate failed
- `draft_unverified`: generated and validator-checked, but not opened in FairyGUI editor
- `editor_accepted`: FairyGUI editor opened and accepted the XML
- `published`: FairyGUI editor published the package
- `unity_smoke_passed`: Unity loaded the package and passed smoke tests

Only `unity_smoke_passed` may be described as production-ready.

## 12. Final Manual Checks

Confirm:

- FairyGUI editor opens the package without repair prompts
- hierarchy and z-order agree with `fgui_spec.md`
- controllers switch every declared page, with `pages` stored as `pageId,pageName` pairs and an in-range `selected` index
- gears, relations, and transitions resolve valid objects and values; `gearLook` states contain five serialized fields and Gear pages reference Controller page IDs
- external Button/Label title and icon overrides affect the intended instance, and their extension type matches the referenced component
- exported Controller parameters affect the intended instance and the parent `controller` page index matches the target Controller pages sequence
- opaque backgrounds are behind all content and transparent frames do not cover the center
- every icon visually matches its approved bitmap source and has no generic procedural-vector appearance
- backgrounds contain environment only; isolated portraits/icons have clean alpha and no screenshot rectangle; frames/panels/buttons contain no baked dynamic text or duplicated child content
- the approved production preview and package use the exact same runtime bitmap files and hashes
- exact-copy/crop claims match the source pixels; reconstructed assets are clearly marked and justified
- every text node matches the approved typography spec and render trace for font, size, color, spacing, stroke/shadow, bounds, preview text, and localization key
- every reusable instance displays the intended portrait, icon, title, state, selected page, and preview values
- component files with data-only differences were consolidated into one base component
- repeated icon-plus-value, icon-plus-title, badge, row, or panel-shell structures use reusable child components when appropriate
- every required visual part listed in `component_visual_parts.json` is visible in the intended component
- no required icon, panel frame, title decoration, separator, background, marker, or text part is missing
- no white placeholder blocks, blank controls, raw localization keys, or accidental duplicated defaults remain
- relations behave at target aspect ratios
- lists instantiate the expected `defaultItem`
- text and localization keys render correctly
- Unity `UIPackage.AddPackage` succeeds
- expected named children and controllers are available to bindings
- publishing creates the expected Unity assets
