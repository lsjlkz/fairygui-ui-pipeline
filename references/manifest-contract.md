# Manifest Contract

## Role

`asset_manifest.json` is the source of truth for art assets, sheet layout, slicing, and FairyGUI mapping. `fgui_id_registry.json` is the source of truth for stable package, resource, and component-instance IDs.

## asset_manifest.json

Recommended top-level shape:

```json
{
  "version": "0.1.0",
  "screen": "cooking_view",
  "resolution": [1920, 1080],
  "orientation": "landscape",
  "style": "bright_cartoon_45deg_cooking",
  "production": {
    "generateFullScreenDesign": true,
    "requiresDesignApproval": true,
    "requiresVisualPartCoverage": true,
    "requiresAssetIsolation": true,
    "requiresProductionPreviewLineage": true,
    "requiresTypographyFidelity": true,
    "generateVisualAssets": true,
    "requiresVisualReference": true
  },
  "referenceImages": [
    {
      "file": "references/ui_reference.png",
      "role": "style_and_layout",
      "resolution": [1920, 1080],
      "isPrimary": true,
      "allowedUses": ["style", "composition", "layout", "asset_generation"]
    }
  ],
  "package": {
    "name": "cooking",
    "outputPath": "fgui_xml/cooking"
  },
  "sheets": [],
  "assets": []
}
```

## Sheet Object

```json
{
  "name": "sheet_food_5x4",
  "file": "generated/sheets/sheet_food_5x4.png",
  "rows": 4,
  "cols": 5,
  "cellSize": [256, 256],
  "padding": [0, 0, 0, 0],
  "items": ["food_patty_raw", "food_patty_cooked"],
  "reviewStatus": "approved",
  "reviewedBy": "user",
  "reviewType": "user_confirmation",
  "reviewEvidence": "reports/asset_isolation_review.md"
}
```

Rules:

- `rows * cols` is the maximum item count.
- Sheet names and files use lowercase snake_case.
- Keep one logical asset per cell.
- Do not place backgrounds and isolated transparent objects in the same sheet.
- A sheet used by `approved_sheet_slice` must be the exact approved resource-preview bitmap, exist under its declared `file`, and record human `reviewStatus`, `reviewedBy`, `reviewType`, and `reviewEvidence`.
- A processed `_alpha`, `_clean`, resized, or otherwise changed bitmap is a different sheet source and must be registered under its real filename.

## Asset Object

```json
{
  "name": "food_patty_raw",
  "file": "fgui_xml/cooking/art/food_patty_raw.png",
  "packageRelativeFile": "art/food_patty_raw.png",
  "type": "ingredient",
  "sourcePixelSize": [256, 256],
  "displaySize": [256, 256],
  "scalePolicy": "pixel_exact",
  "renderMode": "normal",
  "nineSliceGrid": null,
  "transparent": true,
  "trim": true,
  "assetSource": {
    "mode": "approved_sheet_slice",
    "sourceFile": "generated/sheets/sheet_food_5x4.png",
    "crop": [0, 0, 256, 256],
    "reviewStatus": "approved"
  },
  "assetIsolation": {
    "role": "isolated_subject",
    "requiresTransparentBackground": true,
    "forbidNeighborPixels": true,
    "sourceRegionContainsOnlyAsset": true,
    "forbidBakedText": true,
    "reviewStatus": "approved",
    "reviewedBy": "user",
    "reviewType": "user_confirmation",
    "reviewEvidence": "reports/asset_isolation_review.md"
  },
  "pivot": "center",
  "sheet": "sheet_food_5x4",
  "cell": [0, 0],
  "states": ["raw"],
  "fgui": {
    "package": "cooking",
    "resourceType": "image",
    "component": "cooking_view",
    "layer": "ingredient_layer",
    "nodeType": "image",
    "binding": "foodPattyRaw"
  }
}
```

Required fields:

- `name`
- `file`
- `packageRelativeFile`
- `type`
- `sourcePixelSize`
- `displaySize`
- `scalePolicy`
- `renderMode`
- `transparent`
- `pivot`
- `fgui.resourceType`

The legacy `size` field is not sufficient for new production files. Read `references/asset-size-contract.md` before creating or validating bitmap assets.

Read `references/package-resource-path-contract.md` before staging FairyGUI package resources or generating XML. For every file-backed bitmap resource:

```text
asset.file == package.outputPath + "/" + asset.packageRelativeFile
```

`file` is relative to the `UIProduction` root. `packageRelativeFile` is relative to the directory containing `package.xml` and is the only path allowed in fresh component XML `fileName`. Do not write the full `asset.file` value into `package.xml` or component XML.

When `production.generateFullScreenDesign=true`, `production.requiresDesignApproval`, `production.requiresVisualPartCoverage`, `production.requiresAssetIsolation`, `production.requiresProductionPreviewLineage`, and `production.requiresTypographyFidelity` must all be true. Read the design-approval, asset-isolation, production-preview-lineage, typography-fidelity, visual-part, and component-reuse contracts before finalizing the production manifest or entering downstream stages.

## Visual Part Coverage

Every required visible part declared in `specs/component_visual_parts.json` must have an explicit implementation. Asset-backed parts must name an `assets[].name`; Graph fallbacks for detailed parts require explicit human approval; XML node names are validated after generation. Read `references/visual-part-coverage-contract.md`.

When `production.generateVisualAssets=true`, at least one valid primary entry in `referenceImages` is mandatory. Read `references/visual-reference-contract.md` before image generation.

## Bitmap Icon Provenance

Every small art-directed icon asset must include `assetSource` according to `references/bitmap-icon-source-contract.md`.

Allowed production sources are approved design/sheet slices, user-provided bitmaps, existing package bitmaps, or reference-driven image generation with an approval record. Programmatic Graph/SVG/font-glyph/PIL geometry is forbidden for production icons even when it is rasterized to PNG.

Run `scripts/validate_bitmap_asset_provenance.py` before resource generation and XML readiness.

## Asset Isolation

The approved full-screen mockup is a reference-only composition image. It must not be registered as a runtime background or used as a universal rectangular crop sheet.

When `production.requiresAssetIsolation=true`, every bitmap must declare `assetIsolation`. Roles are:

- `environment_background`
- `isolated_subject`
- `isolated_icon`
- `decorative_frame`
- `component_skin`
- `full_screen_reference_only`

Clean backgrounds must contain environment only. Isolated subjects/icons normally require transparent pixels, forbid neighboring screenshot content, and declare that the source region contains only the intended asset. Frames and skins must set `forbidBakedText=true`, `containsBakedText=false`, and `containsDynamicChildContent=false` when text and child content are produced by FairyGUI.

A plain rectangular crop cannot claim UI removal, alpha extraction, neighbor cleanup, baked-text removal, or reconstruction of hidden pixels. For `approved_sheet_slice`, the per-asset `slice_plan` row and `cut_report.json` row must repeat the exact Manifest `sourceFile`, `crop`, and output path. The cut report must freeze source/output SHA-256 and, for `deterministic_transform`, the processor script and its SHA-256. Run `scripts/validate_asset_isolation.py` after resource generation and before XML readiness; retain `reports/asset_isolation_review.md` as human evidence.

## Production Preview Lineage

The design mockup approval does not approve separately generated runtime assets as exact matches. Create `specs/production_preview_lineage.json`, assemble the final preview from exact staged `asset.file` values, and use `reports/production_preview_approval.json` to freeze the preview plus every runtime bitmap SHA-256. Read `references/production-preview-lineage-contract.md`.

Every runtime bitmap must also declare `sourceLineage` in the lineage file:

- `designRelation`: `exact_approved_source`, `exact_provided_source`, or `reference_reconstruction`.
- `derivationMode`: `exact_file`, `exact_crop`, or `deterministic_transform`.
- `sourceFile` and frozen `sourceSha256`.
- `crop` for exact crop.
- `transformScript` plus frozen script hash for deterministic transform.
- `reconstructionReason` whenever the approved/provided image cannot be used exactly.

Use exact provided/self-contained sources before image generation. A generated sheet is not an exact approved-design slice; it must declare reference reconstruction relative to the approved screen.

No runtime image, source, crop, transform script, or production preview may be changed after production-preview approval without superseding that approval.

## Typography Fidelity

Create `specs/typography_spec.json` and use it as the single source for both final preview text and FairyGUI XML text/richtext attributes. Image-model text is reference-only. Exact production text must declare font identity, font size, color, alignment, auto-size, single-line behavior, optional spacing/stroke/shadow, component-local bounds, preview text, and localization mapping. A deterministic preview renderer must write `reports/typography_render_trace.json` in the same run, freezing the current Typography Spec hash and the resolved attributes/bounds/text of every rendered instance. Read `references/typography-fidelity-contract.md`.

Recommended pivot values:

- `center`
- `bottom_center`
- `top_left`
- `[0.5, 0.5]`

## State Matrix

Assets with states should explicitly list them:

```json
{
  "name": "machine_fryer",
  "states": ["idle", "cooking", "done", "burned"]
}
```

Create corresponding FairyGUI controller pages:

- controller: `c_state`
- pages: `idle,cooking,done,burned`

## External Component Parameter Overrides

When a parent component instance overrides a referenced Button or Label, record the intent in `fgui_spec.md` and keep all referenced resources in the registry.

```xml
<component src="btn01" fileName="btn_action.xml">
  <Button title="@ui_confirm" icon="ui://qdf53qpkico01"/>
</component>
```

Rules:

- `src` identifies a component resource whose XML root `extention` matches the child node tag.
- `title` and `selectedTitle` use localization keys for formal UI copy.
- `icon`, `selectedIcon`, and `sound` use registered `ui://{packageId}{resourceId}` URLs.
- Override nodes do not create new assets; every referenced icon or sound must already exist in the manifest/registry/package.
- Every referenced icon must also have valid bitmap provenance; an external `icon` override may not point to a procedurally drawn replacement.
- Every external override field must be declared in `component_state_map.components[].reusePlan.parameterizableFields`.
- Do not create a new component XML merely because an instance needs a different external title or icon.
- Unsupported extension attributes and mismatched child tags are blockers.

## fgui_id_registry.json

Recommended shape:

```json
{
  "version": "0.1.0",
  "packages": {
    "cooking": {
      "id": "qdf53qpk",
      "resources": {
        "food_patty_raw": "mdvn0",
        "cooking_view.xml": "u7u5e"
      },
      "instances": {
        "cooking_view/bg_main": "n0_3qpk",
        "cooking_view/btn_start": "n1_3qpk"
      },
      "retired": []
    }
  }
}
```

Rules:

- First run may generate package/resource IDs.
- Reruns must reuse existing IDs.
- Deleted IDs go into `retired`; do not reuse them casually.
- `src` in XML must use resource IDs from this registry.

## Naming Rules

Use lowercase snake_case for files and asset names:

- `bg_kitchen_main`
- `table_workbench`
- `food_patty_raw`
- `machine_fryer` for one reusable component with idle/done Controller pages
- `btn_start` for one reusable Button component; state belongs to its Button Controller
- `icon_coin`
- `bubble_order_empty`
- `customer_01_idle`

Avoid:

- Chinese asset file names
- pinyin mixed with English
- arbitrary capitalization
- `图层1`
- `button copy`
- `按钮副本`
