# Visual Part Coverage Contract

Use this contract for every complete screen reconstructed from an approved design image.

## Purpose

Structural regions and component types are not sufficient to reproduce a design. Every visible part that contributes to hierarchy, meaning, interaction feedback, framing, decoration, or readability must have an explicit implementation path.

This contract prevents failures such as:

- a required small icon is omitted because the surrounding text still exists
- a panel frame or title decoration disappears because it was treated as optional decoration
- a detailed painted frame is silently replaced by a plain rectangle
- an asset exists in the manifest but is never used by component XML
- component XML contains the main data fields but omits required backgrounds, separators, badges, title bars, or state ornaments

The contract is data-driven. It must not contain project-specific component names, roles, or asset names.

## Required Project File

Complete-screen projects must create:

```text
specs/component_visual_parts.json
```

Recommended shape:

```json
{
  "version": "0.1.0",
  "screen": "screen_name",
  "designSources": [
    "generated/design/screen_design_final.png"
  ],
  "components": [
    {
      "componentType": "ExampleCard",
      "componentFiles": [
        "example_card.xml"
      ],
      "requirementIds": [
        "REQ-EXAMPLE"
      ],
      "parts": [
        {
          "partId": "frame",
          "role": "background_frame",
          "required": true,
          "visibleInApprovedDesign": true,
          "visualImportance": "structural",
          "complexity": "detailed",
          "requirementIds": [
            "REQ-EXAMPLE"
          ],
          "implementation": {
            "mode": "asset_image",
            "assetName": "frame_example_card",
            "xmlNodeNames": [
              "frame"
            ],
            "appliesToFiles": [
              "example_card.xml"
            ],
            "nodeMatch": "all",
            "fallbackPolicy": "forbidden"
          }
        },
        {
          "partId": "value",
          "role": "runtime_value",
          "required": true,
          "visibleInApprovedDesign": true,
          "visualImportance": "semantic",
          "complexity": "simple",
          "requirementIds": [
            "REQ-EXAMPLE"
          ],
          "implementation": {
            "mode": "text",
            "xmlNodeNames": [
              "txt_value"
            ],
            "previewText": "100",
            "runtimeBindings": [
              "value"
            ],
            "fallbackPolicy": "forbidden"
          }
        }
      ]
    }
  ],
  "reviewStatus": "reviewed",
  "blockingForXml": false
}
```

## Required Component Fields

Every component entry must contain:

- `componentType`
- one or more `componentFiles`
- `requirementIds`
- non-empty `parts`

A component file should normally be a reusable base archetype or a composite component. Do not list one file per title, icon, portrait, number, color, or selected-page variation. An explicit preview variant is allowed only under `references/component-reuse-parameterization-contract.md` with a valid structural justification.

## Required Part Fields

Every part must contain:

- `partId`: unique within its component
- `role`: project-defined semantic role
- `required`: boolean
- `visibleInApprovedDesign`: boolean
- `visualImportance`: `structural`, `semantic`, or `decorative`
- `complexity`: `simple` or `detailed`
- `requirementIds`
- `implementation.mode`
- `implementation.xmlNodeNames` for required visible parts
- `implementation.fallbackPolicy`

The role is not selected from a fixed game-specific enum. Projects may use roles such as `background_frame`, `stat_icon`, `title_decoration`, `selection_marker`, or any other meaningful identifier.

## Implementation Modes

Allowed modes:

- `asset_image`: package bitmap referenced by an `<image>` or `<loader>`
- `runtime_loader`: runtime-selected image displayed by a `<loader>`; a readable preview asset or preview state is still required
- `graph`: FairyGUI vector Graph
- `text`: FairyGUI text or rich-text object
- `child_component`: referenced FairyGUI component
- `group`: structural FairyGUI group
- `none`: allowed only when `required=false` or `visibleInApprovedDesign=false`

### Asset-backed Parts

`asset_image` and `runtime_loader` require:

- `assetName`
- a matching `asset_manifest.json.assets[].name`
- a registered package resource
- an XML node that resolves to that resource when XML exists

### Icon-Like Parts

Small art-directed icons, badges, crests, and emblems must use an approved bitmap path. Their implementation mode must be `asset_image`, `runtime_loader`, or an asset-backed `child_component`.

Do not use FairyGUI Graph, SVG, font glyphs, PIL/ImageDraw geometry, or other procedural vector-like drawing to imitate production icons. Read `references/bitmap-icon-source-contract.md` and require Manifest `assetSource` provenance.

Graph remains appropriate for plain separators, progress fills, translucent state overlays, hit areas, and debug geometry when those shapes are not intended to reproduce an art-directed icon.

### Detailed Parts and Graph Downgrade

A part with `complexity=detailed` must not use `mode=graph` unless all of the following are present:

```json
{
  "fallbackPolicy": "approved",
  "fallbackApproval": {
    "status": "approved",
    "recordedBy": "user",
    "note": "The exact visual downgrade was accepted."
  }
}
```

AI self-approval is invalid. Missing approval produces:

```text
visual_part_degraded_to_graph_without_approval
```

### Text Parts

A required preview text part must not be blank or expose an unresolved localization key.

Recommended XML:

```xml
<text name="title" text="READABLE PREVIEW" customData="loc:ui_key"/>
```

### Reusable Part Structure

When multiple components contain the same stable visual substructure, such as icon-plus-value, icon-plus-title, badge-plus-text, or a titled panel shell, extract it as a reusable child component when practical. Declare that child in the owning semantic component's `reusePlan.childComponentFiles` and represent it with `implementation.mode=child_component` where appropriate.

A visual-part list must not legitimize duplicate variants. If several files have the same required nodes and differ only in content values, consolidate them into one base file and configure instances externally.

### File Scope

By default, a part applies to every file in `componentFiles`.

Use `implementation.appliesToFiles` when only selected variants contain the part.

`implementation.nodeMatch` may be:

- `all`: every declared node name is required
- `any`: at least one declared node name is required

## Required `fgui_spec.md` Table

Complete-screen assembly plans must include:

```markdown
## Visual Part Coverage

| Component Type | Part ID | Role | Required | Importance | Complexity | Implementation Mode | Asset Name | XML Nodes | Applies To Files | Fallback Policy | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|---|---|
```

Every `component_visual_parts.json` part must have exactly one matching row.

## Validation Stages

### `asset_planning`

Validate:

- the coverage file exists and is structurally complete
- approved-design sources are recorded
- every required asset-backed part exists in the manifest
- detailed parts are not silently downgraded to Graph

### `fairygui_assembly`

Additionally validate:

- `fgui_spec.md` contains the Visual Part Coverage table
- every declared part is represented in the table

### `xml_generation`

When XML is available, additionally validate:

- required component files exist
- required named nodes exist in the intended files
- node tags match the implementation mode
- asset-backed nodes use the declared manifest asset
- required preview text is readable
- localization identity is preserved when declared

## Hard Blocking Rules

Block downstream work when:

- `component_visual_parts.json` is missing for an approved complete-screen design
- a required visible part has no implementation
- a required asset-backed part is absent from the manifest
- a required XML node is missing
- a declared asset exists but the XML node references another resource
- a detailed part is replaced by Graph without explicit human approval
- an icon, badge, crest, or emblem uses Graph or another procedural/vector-like substitute instead of an approved bitmap
- an icon asset lacks a valid `assetSource` provenance record
- a required preview text is blank or displays an unresolved localization key
- multiple component files exist only to carry different titles, icons, portraits, values, colors, sizes, or default pages
- a repeated stable substructure is duplicated across variants instead of being parameterized or extracted as a reusable child, without an explicit justification
- the coverage table omits a declared part
- `blockingForXml=true`

## Reports

Write:

```text
reports/visual_part_coverage_report.json
reports/visual_part_coverage_report.md
```

A passing structural report does not replace the FairyGUI screenshot comparison with the exact approved design.