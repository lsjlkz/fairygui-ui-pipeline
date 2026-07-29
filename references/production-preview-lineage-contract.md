# Production Preview Asset Lineage Contract

## Purpose

A full-screen design mockup may establish composition, hierarchy, style, and asset shape, but it does not prove that separately generated production assets are pixel-identical to the approved screen.

This contract prevents a pipeline from approving one image and then silently generating a different background, portrait, icon sheet, panel skin, or button skin for FairyGUI.

## Two Approval Gates

Full-screen projects use two distinct approvals:

1. **Design mockup approval**: approves composition, hierarchy, visual direction, and approximate asset appearance.
2. **Production preview approval**: approves the exact staged runtime bitmaps, deterministic text rendering, and final assembled appearance.

The first approval permits decomposition and resource production. It does not approve future image-model reinterpretations as exact runtime assets.

When a user-provided bitmap or a self-contained approved-design region is already suitable for production, it is the authoritative source and must be copied or cropped deterministically. Do not regenerate it merely to obtain a similar-looking asset. Reference-driven regeneration is allowed only when exact extraction is impossible, such as occluded backgrounds, non-isolated portraits, missing transparent edges, or unseen state variants; the lineage must state that limitation explicitly.

## Required Production Declaration

```json
{
  "production": {
    "generateFullScreenDesign": true,
    "requiresProductionPreviewLineage": true
  }
}
```

Complete-screen projects must create:

```text
specs/production_preview_lineage.json
reports/production_preview_approval.json
reports/production_preview_lineage_report.json
reports/production_preview_lineage_report.md
```

## Core Rule

The final production preview must be assembled from the exact files that will enter the FairyGUI package.

Correct:

```text
approved or generated isolated source
-> deterministic crop/cleanup
-> staged runtime PNG
-> production preview uses that exact staged PNG
-> human approves preview and runtime hashes
-> XML references the same staged PNG
```

Incorrect:

```text
approved design mockup
-> new image-model generation for preview
-> another image-model generation for sheets
-> crop sheets for FairyGUI
```

The incorrect flow may produce a similar style, but it cannot claim exact preview fidelity.

## Do Not Universally Slice The Flat Screen

The rule is not “all assets must be rectangular crops from the flattened full-screen preview.” A flat screen cannot safely provide:

- environment pixels hidden behind UI or characters;
- transparent portraits when the visible source includes a background;
- state variants not visible in the screen;
- clean panel/button skins when text or child content is visible;
- reusable assets whose boundaries overlap other content.

Instead, first produce clean standalone assets. Then assemble the production preview from those exact standalone files.

Direct cropping from the approved design is allowed only when the region is already self-contained, unoccluded, free of neighboring pixels, and compatible with the required transparency/content rules.

## Fidelity Modes

Allowed `fidelityMode` values:

- `exact_production_composite`: final preview is assembled from exact staged runtime files.
- `direct_source_assets`: a provided production-ready screen/source already contains exact self-contained assets, and declared exact crops are used.
- `reference_reinterpretation`: image generation uses the mockup as a reference. This is allowed during resource exploration but cannot be the final approved production preview.

At `fairygui_assembly`, `xml_generation`, and `validation`, `reference_reinterpretation` is blocking.

## Required Project File

```json
{
  "version": "0.1.0",
  "screen": "screen_name",
  "fidelityMode": "exact_production_composite",
  "productionPreview": {
    "file": "generated/preview/assembled_screen.png",
    "sha256": "<preview-sha256>",
    "rendererScript": "scripts/render_production_preview.py",
    "usesProductionAssets": true,
    "approvalRecord": "reports/production_preview_approval.json"
  },
  "assets": [
    {
      "assetName": "icon_example",
      "runtimeFile": "fgui_xml/package/art/icon_example.png",
      "runtimeSha256": "<runtime-file-sha256>",
      "previewUsage": "exact_file",
      "sourceLineage": {
        "designRelation": "exact_provided_source",
        "derivationMode": "exact_file",
        "sourceFile": "references/icon_example.png",
        "sourceSha256": "<source-file-sha256>"
      }
    },
    {
      "assetName": "state_not_visible",
      "runtimeFile": "fgui_xml/package/art/state_not_visible.png",
      "runtimeSha256": "<runtime-file-sha256>",
      "previewUsage": "not_visible",
      "reason": "Disabled state is not active in the approved production preview."
    }
  ],
  "blockingForXml": false
}
```

Allowed `previewUsage` values:

- `exact_file`: preview renderer loads the exact runtime file.
- `exact_crop`: runtime file and preview both come from the same declared self-contained source region.
- `not_visible`: the runtime asset is a state/variant not visible in the selected preview; a reason is mandatory.

Every runtime bitmap in `asset_manifest.json` must have one lineage entry.

## Source Lineage

Every lineage asset entry must contain `sourceLineage` with two independent decisions:

- `designRelation`: how the asset relates to the approved design or user-provided source.
- `derivationMode`: how the exact runtime bytes/pixels were produced.

Allowed `designRelation` values:

- `exact_approved_source`: exact self-contained region from the approved design.
- `exact_provided_source`: exact user/project-provided production bitmap.
- `reference_reconstruction`: separately generated or reconstructed from references because exact extraction is impossible.

Allowed `derivationMode` values:

- `exact_file`: runtime bytes equal source bytes.
- `exact_crop`: runtime pixels equal the declared source crop with no resize, redraw, or reinterpretation.
- `deterministic_transform`: a declared script performs necessary deterministic trim, alpha cleanup, resize, or composition.

`exact_file` and `exact_crop` are machine-checked. `deterministic_transform` must freeze the source hash, transform script path, and transform script hash. `reference_reconstruction` must include `reconstructionReason`; it cannot claim pixel identity with the approved design and therefore requires final production-preview approval.

Example reconstructed sheet asset:

```json
{
  "sourceLineage": {
    "designRelation": "reference_reconstruction",
    "reconstructionReason": "The approved screen contains background and neighboring UI behind the icon, so exact transparent extraction is impossible.",
    "derivationMode": "deterministic_transform",
    "sourceFile": "generated/sheets/ui_icon_sheet.png",
    "sourceSha256": "<sheet-sha256>",
    "transformScript": "scripts/process_generated_assets.py",
    "transformScriptSha256": "<script-sha256>"
  }
}
```

Source-mode consistency rules:

- `assetSource.mode=provided_bitmap` requires `designRelation=exact_provided_source`.
- `assetSource.mode=approved_design_slice` requires `designRelation=exact_approved_source`.
- `assetSource.mode=image_generation_with_reference` requires `designRelation=reference_reconstruction`.
- `assetSource.mode=approved_sheet_slice` requires `sourceLineage.sourceFile` and `sourceLineage.crop` to exactly equal `assetSource.sourceFile` and `assetSource.crop`; the same source/crop must also appear in `slice_plan.json` and `reports/cut_report.json`.
- A generated sheet may be the deterministic derivation source, but it remains a reference reconstruction relative to the approved screen unless that exact standalone sheet has separately become the approved authoritative source.

For a processed sheet, the actual processed bitmap is the lineage source. If the slicer opens `ui_icon_sheet_alpha.png`, neither Manifest nor lineage may claim that `ui_icon_sheet.png` was the source. The processed sheet must be registered, human-reviewed, hashed, and referenced by its real path.

## Production Preview Approval

After the exact runtime assets and deterministic typography are assembled:

```bash
python scripts/record_production_preview_approval.py \
  --root UIProduction \
  --action pending \
  --note "Waiting for human approval of exact runtime assets and typography"
```

Present the exact production preview to the user and stop.

After explicit human confirmation:

```bash
python scripts/record_production_preview_approval.py \
  --root UIProduction \
  --action approve \
  --confirmation-type user_confirmation \
  --recorded-by user \
  --note "User approved this exact production preview and runtime asset set"
```

The approval record freezes:

- exact production preview file and SHA-256;
- every runtime asset name and SHA-256;
- `production_preview_lineage.json` SHA-256;
- available `typography_spec.json` and `typography_render_trace.json` SHA-256 values;
- human confirmation type, reviewer, note, and time.

After approval, no runtime bitmap may be regenerated, replaced, re-cropped, or post-processed without superseding the approval and repeating the production-preview review.

## Required Stage Order

```text
design mockup approval
-> semantic/layout analysis
-> resource generation and slicing
-> package staging
-> deterministic typography specification
-> production preview assembled from exact staged assets
-> production preview human approval
-> XML readiness
-> XML generation
-> FairyGUI editor comparison
```

## Blocking Conditions

- `production_preview_lineage_not_required`
- `production_preview_lineage_missing`
- `reference_reinterpretation_cannot_be_final_preview`
- `approved_preview_not_composed_from_production_assets`
- `runtime_asset_missing_from_preview_lineage`
- `preview_runtime_file_manifest_mismatch`
- `runtime_asset_not_used_by_preview_renderer`
- `production_preview_hash_mismatch`
- `production_asset_regenerated_after_preview_approval`
- `production_preview_approval_missing`
- `production_preview_not_approved`
- `production_preview_approval_hash_mismatch`
- `production_preview_asset_hashes_missing`
- `approved_preview_asset_hash_mismatch`
- `production_preview_evidence_hashes_missing`
- `production_preview_evidence_hash_mismatch`
- `production_preview_evidence_file_missing`
- `production_preview_ai_self_approval_forbidden`
- `runtime_asset_source_lineage_missing`
- `runtime_asset_design_relation_invalid`
- `runtime_asset_derivation_mode_invalid`
- `runtime_asset_reconstruction_reason_missing`
- `runtime_asset_source_hash_missing`
- `runtime_asset_source_hash_mismatch`
- `runtime_asset_exact_file_mismatch`
- `runtime_asset_exact_crop_pixel_mismatch`
- `runtime_asset_transform_script_missing`
- `runtime_asset_transform_script_hash_mismatch`
- `generated_asset_must_declare_reference_reconstruction`
- `provided_asset_must_use_exact_source_relation`
- `approved_design_slice_must_use_exact_relation`
- `approved_sheet_source_not_registered`
- `runtime_asset_manifest_source_mismatch`
- `runtime_asset_manifest_crop_mismatch`
- `approved_sheet_derivation_mode_invalid`

## Validation Command

```bash
python scripts/validate_production_preview_lineage.py \
  --root UIProduction \
  --stage xml_generation \
  --out UIProduction/reports/production_preview_lineage_report.json \
  --report-md UIProduction/reports/production_preview_lineage_report.md
```

A design approval, asset-isolation pass, or XML structural pass does not replace this gate. Those checks answer different questions.
