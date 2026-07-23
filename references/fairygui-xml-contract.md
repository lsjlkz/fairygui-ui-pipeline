# FairyGUI XML Contract Gate

This file is the short operational gate for XML work. It is not the full XML specification.

For any task that generates, reviews, repairs, or validates FairyGUI XML, read both embedded complete source documents first:

```text
references/fairygui-ai-generation-workflow.md
references/fairygui-xml-parsing-specification.md
```

Also read `references/fairygui-xml-parsing-spec.md` as the local index. Do not use this contract, `SKILL.md`, prior memory, an index, or any summary as a substitute for the embedded complete documents.

## Hard Gate

Do not generate `package.xml` or component XML unless all of these are available:

- complete embedded workflow: `references/fairygui-ai-generation-workflow.md`
- complete embedded XML specification: `references/fairygui-xml-parsing-specification.md`
- XML procedure checklist: `references/xml-strict-generation.md`
- manifest: `asset_manifest.json`
- stable ID registry: `fgui_id_registry.json`
- FairyGUI assembly plan: `fgui_spec.md` or equivalent
- package name and package ID
- resource IDs for all images, components, sounds, fonts, movieclips, atlases, and misc resources used by XML
- component instance IDs or permission to create stable new IDs
- `references/design-mockup-approval-contract.md` when a complete screen design was generated from requirements/design documents
- a passing `design_approval.json` record for `xml_generation`, bound to the exact approved image SHA-256
- `references/asset-size-contract.md`
- `references/semantic-controller-mapping-contract.md`
- `references/component-reuse-parameterization-contract.md`
- `references/component-instance-configuration-contract.md`
- `references/display-list-z-order-contract.md`
- `references/bitmap-icon-source-contract.md`
- `references/visual-part-coverage-contract.md`
- `references/package-resource-path-contract.md`
- a passing `scripts/validate_semantic_controller_mapping.py --stage xml_generation` report
- a passing `scripts/validate_component_reuse.py --stage xml_generation` report
- a passing `scripts/validate_display_list_z_order.py --stage xml_generation` report
- a passing `scripts/validate_bitmap_asset_provenance.py --stage xml_generation` report
- valid visual-reference declarations when visual assets were generated or reconstructed
- `sourcePixelSize`, `displaySize`, `scalePolicy`, and `renderMode` for every bitmap
- `packageRelativeFile` for every file-backed package resource
- staged files present at `package.outputPath/packageRelativeFile`

If anything is missing, output `XML生成阻塞报告` instead of XML.

When project files are accessible, enforce this gate with:

```bash
python scripts/verify_embedded_docs.py
python scripts/validate_semantic_controller_mapping.py --root UIProduction --stage xml_generation --out UIProduction/reports/semantic_controller_mapping_report.json --report-md UIProduction/reports/semantic_controller_mapping_report.md
python scripts/validate_component_reuse.py --root UIProduction --stage xml_generation --out UIProduction/reports/component_reuse_report.json --report-md UIProduction/reports/component_reuse_report.md
python scripts/validate_display_list_z_order.py --root UIProduction --stage xml_generation --out UIProduction/reports/display_list_z_order_report.json --report-md UIProduction/reports/display_list_z_order_report.md
python scripts/validate_bitmap_asset_provenance.py --root UIProduction --stage xml_generation --out UIProduction/reports/bitmap_asset_provenance_report.json --report-md UIProduction/reports/bitmap_asset_provenance_report.md
python scripts/validate_visual_part_coverage.py --root UIProduction --stage xml_generation --out UIProduction/reports/visual_part_coverage_report.json --report-md UIProduction/reports/visual_part_coverage_report.md
python scripts/check_xml_readiness.py --root UIProduction --profile fresh --require-design-approval --resource-generation --design-driven --out UIProduction/reports/xml_readiness_report.json --report-md UIProduction/reports/xml_blocking_report.md --snapshot-out UIProduction/reports/xml_generation_input_snapshot.json
```

Use `--require-design-approval` whenever the complete-screen design was generated from requirements/design documents. Use `--design-driven` whenever a design image participates in layout. Use `--resource-generation` whenever this pipeline generated, redrew, restyled, or reconstructed bitmap resources.

## Required Spec Coverage

The full XML spec includes rules that must not be dropped:

- package resource node types: `component`, `image`, `sound`, `movieclip`, `font`, `atlas`, `misc`
- component root attributes: `size`, `pivot`, `pivotAsAnchor`, `extention`, `remark`, `overflow`, `clipSoftness`
- controller and action attributes
- displayList object rules
- common object attributes and filter attributes
- `image`, `loader`, `text`, `richtext`, `graph`, `list`, and `group`
- extension nodes: `Button`, `Label`, `ComboBox`, `ProgressBar`, `Slider`, `ScrollBar`, `Tree`
- extension parameter child nodes on component instances, such as `<component ...><Button title="..." icon="ui://..."/></component>` and `<component ...><Label title="..." icon="ui://..."/></component>`, including target-extension matching and URL validation
- internal child naming conventions for extension components
- editor-export compatibility attributes that appear in verified FairyGUI project XML
- Relation system and `sidePair` values
- Gear system, gear tween rules, and controller/page validation
- Transition attributes and `TransitionActionType` enum
- package/object/layout/fill/selection/button/group/fill-method enumerations
- branch and high-resolution mechanisms
- naming rules, resource organization rules, AI generation constraints
- manifest-to-XML mapping
- ID registry and stable regeneration rules
- validation rules
- reuse-first component planning, parameterizable fields, reusable child components, and justified structural variants
- per-instance configuration rules for reusable components, including base-component defaults and readable preview values
- visual-part coverage rules for required icons, frames, title decorations, backgrounds, separators, markers, and text nodes
- UI adaptation and localization rules

## Non-Negotiable XML Rules

- `packageDescription@id` is an 8-character lowercase alphanumeric package ID.
- package resource IDs are stable lowercase alphanumeric IDs copied from `package.xml`, `asset_manifest.json`, or `fgui_id_registry.json`. The default generator may create 5-character IDs, but existing FairyGUI exports/examples can contain other lowercase alphanumeric lengths.
- component instance IDs should follow `n{index}_{packageIdLast4}` for newly generated XML, but valid existing exported IDs should be preserved during repair unless the user asks to normalize them.
- `src` is a resource ID, not an asset name and not a file name.
- `fileName` is the exact package-relative file path from Manifest `packageRelativeFile`, not the UIProduction-root-relative `file` path.
- Every fresh `<image>` has explicit `size` equal to Manifest `displaySize`.
- The real bitmap dimensions equal Manifest `sourcePixelSize`.
- Undeclared scaling is forbidden; size differences require an allowed `scalePolicy`.
- `pkg` is used only for cross-package references.
- `ui://` URLs are `ui://{packageId}{resourceId}` with no slash or separator.
- `component@name` inside `package.xml` is the XML file name, such as `login_panel.xml`.
- package resource `path` starts and ends with `/`.
- `package.xml path + name` resolves to a real file under the directory containing `package.xml`.
- fresh validation uses exact package-relative paths; basename-only equality is forbidden.
- every reusable semantic component must declare one base component and a verifiable reuse strategy; every visual instance must have exactly one matching parent XML instance.
- an instance-level finite state must prefer an exported Controller: target `controller@exported=true`, semantic `controllerParameters`, and parent `controller="name,pageIndex"`.
- title, icon, portrait, value, color, size, localization, or selected-page differences alone must use parameters, Controllers, runtime binding, or reusable child components rather than separate XML files.
- separate variant XML files require a valid structural or compatibility justification and must not have an identical normalized hierarchy.
- `<displayList>` is back-to-front: opaque backgrounds are earliest; later full-size objects require explicit transparent-frame/overlay intent.
- small art-directed icons require approved bitmap provenance; Graph/SVG/font glyph/PIL geometry substitutes are forbidden.
- every required visible part declared in `component_visual_parts.json` must resolve to a Manifest asset, XML node, text node, child component, group, or explicitly approved fallback.
- detailed visual parts may not be silently replaced by Graph without recorded human approval.
- justified variant component default Controller pages must match `component_state_map.visualInstances.controllerPages`.
- approved-design preview text must be readable before runtime localization; unresolved visible `@ui_...` keys are forbidden unless editor resolution is verified.
- output XML is a draft until opened, visually compared with the approved design, checked, and published by FairyGUI editor.

## Validation Profiles

The XML validator must inspect component-instance extension parameter nodes, not merely allow their tag names. It must resolve the target component XML and verify matching `extention`, legal override attributes, and registered `ui://` references.

Use two modes when judging XML:

- **`fresh`**: newly generated XML. Instance IDs must follow the generator convention, manifest file mapping must resolve, and editor-only attributes require an explicit reason in `fgui_spec.md`.
- **`editor-compatible`**: XML already accepted, cleaned, or exported by FairyGUI editor. Preserve valid existing instance IDs and editor-compatible forms, but keep broken references, placeholders, duplicate IDs, malformed XML, and pseudo tags as hard errors.

Do not use `editor-compatible` to bypass failures in newly generated XML.

## Editor Export Compatibility

Apply the selected profile as follows:

- **AI new-generation mode**: prefer the core attributes documented in the full XML spec. Do not invent editor-only attributes unless they are present in the manifest, a real FairyGUI export, or an explicit user rule.
- **Editor-cleaned compatibility mode**: if XML has already passed through FairyGUI editor cleanup/export, preserve known editor attributes and extension parameter nodes unless they break package/resource/controller references.

Known editor-compatible attributes seen in the project include `designImageOffsetY`, `aspect`, `group`, `controller`, `advanced`, `anchor`, `clearOnPublish`, `autoClearText`, `autoPlay`, and `autoPlayRepeat`. Treat these as allowed compatibility attributes during review/repair. For fresh AI XML, only emit them when the current component actually needs the editor behavior and the reason is recorded in `fgui_spec.md`.

A child extension node such as `<Button title="..." icon="ui://..."/>` or `<Label title="..." icon="ui://..."/>` under a `<component>` instance is a valid external parameter/override pattern when the referenced component has the matching `extention`. A reusable exported Controller is passed through the parent instance as `controller="name,pageIndex"`, where the target Controller has `exported="true"`. Do not flag these patterns as pseudo XML.

For fresh XML, validate all of the following:

- the component instance `src` resolves to a component resource
- any `component@controller` value resolves to an exported Controller in that resource and uses a valid zero-based page index
- the referenced component XML root `extention` matches the child node tag exactly
- only attributes allowed by that extension type are used
- `icon`, `selectedIcon`, `sound`, and other `ui://` attributes resolve to registered package resources
- conflicting extension parameter child nodes are forbidden

For editor-compatible XML, preserve editor-accepted override nodes, but broken component references, mismatched extension types, and unresolved URLs remain errors.

## Forbidden Output

Never output XML containing:

- unresolved placeholders such as `包ID`, `资源ID`, `背景资源ID`, `按钮资源ID`, `xxxx`, `{packageId}`, `{resourceId}`
- pseudo nodes such as `panel`, `sprite`, `container`, `layer`, `button` as lowercase free-form tags
- `src` values that match asset names or file names instead of registered resource IDs
- `ui://` URLs that do not resolve to registered package/resource IDs
- controller, gear, relation, transition references that cannot be checked from the component tree
- Controller pages or Gear mappings that cannot be traced to requirement/design evidence and `component_state_map.json`
- image sizes that conflict with Manifest `displaySize`
- bitmap files whose actual pixels conflict with `sourcePixelSize`
- `package.xml` resources whose `path + name` do not exist under the package directory
- component `fileName` values that contain the UIProduction output prefix instead of `packageRelativeFile`
- component instance extension parameter nodes whose tag does not match the referenced component root `extention`
- Button/Label external `icon`, `selectedIcon`, or `sound` URLs that do not resolve to registered resources
- unsupported attributes on external Button/Label override nodes
- semantically different reusable instances that all use an unconfigured default component
- reusable components without `reusePlan` or without a matching Component Reuse Plan row
- exported Controller parameters missing from the target XML or encoded with the wrong page index in the parent
- opaque backgrounds or large covering components placed after normal content
- icon assets without approved bitmap provenance or generated through procedural vector-like scripts
- separate XML files created only for different titles, icons, portraits, values, colors, dimensions, localization keys, or default Controller pages
- structurally identical variant XML files that should use one base component
- composite components that fail to reference declared reusable child components
- justified variant component files whose selected Controller pages disagree with their visual-instance declaration
- missing visual-instance rows in `fgui_spec.md` or missing parent XML instances
- missing required visual-part rows, Manifest assets, component nodes, or package resource references
- detailed visual parts degraded to Graph without explicit human approval
- approved-design previews containing raw localization keys, blank controls, white placeholder blocks, unintended duplicated default content, or omitted icons/frames/titles
- visual-resource generation without a valid primary reference image
- XML generated from a pending, rejected, superseded, modified, or AI-self-approved full-screen design

## Validation

After new XML generation, run:

```bash
python scripts/validate_fgui_xml.py --xml-dir UIProduction/fgui_xml/<package_name> --manifest UIProduction/manifests/asset_manifest.json --registry UIProduction/manifests/fgui_id_registry.json --mode fresh --out UIProduction/reports/xml_validate_report.json
```

After FairyGUI editor cleanup/export, rerun with `--mode editor-compatible` and store a separate report.

If validation cannot run, state that the XML is unverified and list the unchecked risks.
