# Asset Isolation Contract

## Purpose

A production bitmap must contain only the visual material assigned to that asset. File existence, package IDs, XML node coverage, and approved-design provenance do not prove that a bitmap is a valid standalone asset.

This contract prevents:

- using an approved full-screen UI mockup as a runtime background;
- rectangular crops that retain neighboring controls, text, shadows, panel colors, or characters;
- portraits and icons with opaque screenshot backgrounds;
- panel, card, frame, bar, or button skins with baked dynamic text or child content;
- claiming that a plain crop removed UI, extracted alpha, or reconstructed occluded pixels;
- accepting an asset contact sheet without per-asset isolation evidence.

The contract is generic. Project component names and asset roles remain in project files.

## Required production declaration

A project that generates a complete-screen design must declare:

```json
{
  "production": {
    "generateFullScreenDesign": true,
    "requiresAssetIsolation": true
  }
}
```

When `requiresAssetIsolation=true`, every production bitmap in `manifests/asset_manifest.json` must declare `assetIsolation`.

## Isolation roles

Allowed structural roles:

- `environment_background`: environment only; no runtime UI, titles, buttons, panels, portraits, or other screen content.
- `isolated_subject`: transparent standalone character, portrait, prop, or other subject.
- `isolated_icon`: standalone icon, badge, crest, emblem, or intentionally plated icon.
- `decorative_frame`: border, title plate, ornament, or frame without dynamic text or child content.
- `component_skin`: panel, card, bar, row, or button skin without dynamic text or child content.
- `full_screen_reference_only`: design/reference image that must never be staged as a runtime package resource.

## Required fields

Example isolated subject:

```json
{
  "name": "portrait_example",
  "type": "portrait",
  "transparent": true,
  "assetSource": {
    "mode": "image_generation_with_reference",
    "sourceFile": "generated/assets/portrait_example.png",
    "referenceFiles": [
      "generated/design/screen_design_final.png"
    ]
  },
  "assetIsolation": {
    "role": "isolated_subject",
    "requiresTransparentBackground": true,
    "forbidNeighborPixels": true,
    "sourceRegionContainsOnlyAsset": true,
    "forbidBakedText": true,
    "occlusionPolicy": "not_occluded",
    "reviewStatus": "approved",
    "reviewedBy": "user",
    "reviewType": "user_confirmation",
    "reviewEvidence": "reports/asset_isolation_review.md"
  }
}
```

Example component skin:

```json
{
  "assetIsolation": {
    "role": "component_skin",
    "requiresTransparentBackground": false,
    "forbidNeighborPixels": true,
    "sourceRegionContainsOnlyAsset": true,
    "forbidBakedText": true,
    "containsBakedText": false,
    "containsDynamicChildContent": false,
    "reviewStatus": "approved",
    "reviewedBy": "designer",
    "reviewType": "designer_review",
    "reviewEvidence": "reports/asset_isolation_review.md"
  }
}
```

Example clean environment:

```json
{
  "assetIsolation": {
    "role": "environment_background",
    "cleanEnvironmentOnly": true,
    "forbidBakedText": true,
    "containsBakedText": false,
    "containsDynamicChildContent": false,
    "occlusionPolicy": "not_occluded",
    "reviewStatus": "approved",
    "reviewedBy": "qa",
    "reviewType": "qa_review",
    "reviewEvidence": "reports/asset_isolation_review.md"
  }
}
```

Allowed review types:

- `user_confirmation`
- `human_visual_review`
- `artist_review`
- `designer_review`
- `qa_review`

`reviewedBy` must identify a human, user, artist, designer, or QA reviewer. Values such as `ai`, `assistant`, `model`, `agent`, `chatgpt`, or `codex` are invalid self-approval.

## Allowed source modes

- `provided_bitmap`
- `existing_package_bitmap`
- `approved_design_slice`
- `approved_sheet_slice`
- `image_generation_with_reference`
- `manual_reconstruction`
- `inpainted_environment`

`approved_design_slice` is valid only when the source region is already self-contained. Cropping does not imply any of the following:

- removal of UI or text;
- alpha extraction;
- removal of neighboring pixels;
- reconstruction of hidden environment pixels;
- removal of dynamic child content;
- creation of a clean panel or button skin.

`approved_sheet_slice` is valid only when all four declarations identify the same exact resource-preview bitmap:

- `manifest.sheets[].file`;
- `asset.assetSource.sourceFile`;
- `slice_plan.sourceImages[]` and the asset slice row's `sourceFile`;
- `cut_report.outputs[].sourceFile`.

A chroma-key-removed, alpha-cleaned, upscaled, or otherwise processed sheet is a different source file. It must be registered and reviewed under its real filename; the project must not declare the original sheet while the slicing script opens an `_alpha`, `_clean`, or alternate bitmap.

## Hard rules

### Approved full-screen mockups are references

The complete approved UI mockup must not be registered as an environment background or other runtime package asset.

A background whose crop equals the full approved-design bounds is blocked. A clean background must come from a separate environment-only source, an inpainted result, or a reviewed reconstruction.

Blocking codes:

- `asset_isolation_gate_not_required`
- `full_screen_design_used_as_runtime_background`
- `environment_background_source_not_clean`
- `full_screen_reference_registered_as_runtime_asset`

### Plain crop cannot claim isolation

A crop-only script cannot create an asset that requires alpha extraction, neighbor cleanup, UI removal, or occlusion reconstruction.

A `slice_plan.json` row must not use `from_sheet`, `crop`, or `slice_static` while its reason claims a clean environment, transparent subject, separated text, UI removal, or reconstruction.

Blocking codes:

- `plain_rectangular_crop_used_for_isolated_asset`
- `slice_plan_claims_unimplemented_isolation`
- `crop_claims_occlusion_reconstruction`

### Approved resource-preview sheet lineage

After sheet slicing, `reports/cut_report.json` must contain exactly one row per `approved_sheet_slice` asset. Each row must freeze:

- asset name and exact Manifest output path;
- exact source file actually read by the slicer;
- exact `[x,y,width,height]` crop;
- `derivationMode=exact_crop` or `deterministic_transform`;
- source and output SHA-256;
- processor script path and SHA-256 for deterministic transforms.

For `exact_crop`, output pixels must equal the declared source crop without resize or cleanup. For `deterministic_transform`, the recorded processor script must exist and its current hash must match. A report that only lists output filenames is insufficient.

Blocking codes include:

- `approved_sheet_source_not_registered`
- `slice_plan_missing_approved_sheet_source`
- `slice_plan_asset_missing`
- `slice_plan_source_mismatch`
- `slice_plan_crop_mismatch`
- `slice_plan_output_mismatch`
- `slice_plan_derivation_mode_invalid`
- `approved_sheet_review_not_approved`
- `approved_sheet_reviewer_missing`
- `approved_sheet_review_type_invalid`
- `approved_sheet_ai_self_approval_forbidden`
- `approved_sheet_review_evidence_missing`
- `cut_report_missing`
- `cut_report_not_ok`
- `cut_report_asset_missing`
- `cut_report_asset_not_ok`
- `cut_report_asset_duplicate`
- `cut_report_source_mismatch`
- `cut_report_crop_mismatch`
- `cut_report_output_mismatch`
- `cut_report_derivation_mode_invalid`
- `cut_report_source_hash_missing`
- `cut_report_source_hash_mismatch`
- `cut_report_output_hash_missing`
- `cut_report_output_hash_mismatch`
- `cut_report_exact_crop_pixel_mismatch`
- `cut_report_processor_script_missing`
- `cut_report_processor_script_hash_missing`
- `cut_report_processor_script_hash_mismatch`

### Isolated subjects and icons

For transparent subjects/icons:

- `asset.transparent=true`;
- `requiresTransparentBackground=true`;
- `forbidNeighborPixels=true`;
- `sourceRegionContainsOnlyAsset=true`;
- generated pixels must contain usable alpha after resource generation;
- screenshot-like opaque rectangular edges are blocked unless a reviewed intentional plate is declared.

Blocking codes:

- `asset_isolation_declaration_missing`
- `isolated_asset_manifest_not_transparent`
- `isolated_asset_requires_transparency`
- `isolated_asset_opaque_rectangle`
- `isolated_asset_neighbor_pixels_not_forbidden`
- `approved_design_slice_not_self_contained`

### Dynamic content stays in FairyGUI

Decorative frames and component skins must not contain:

- localized titles;
- numeric values;
- button labels;
- progress values;
- selected/disabled state content;
- reusable row/card child content;
- content that XML will add again.

They must declare:

```json
{
  "forbidBakedText": true,
  "containsBakedText": false,
  "containsDynamicChildContent": false
}
```

Blocking codes:

- `dynamic_component_asset_allows_baked_text`
- `asset_isolation_baked_text_not_reviewed`
- `asset_contains_dynamic_child_content`

## Stage behavior

At `asset_planning`:

- the gate declaration and every bitmap's `assetIsolation` plan are required;
- future `reviewEvidence` paths must be declared;
- full-screen-background and crop-plan contradictions already block.

At `resource_generation` and later:

- output bitmap files must exist;
- registered resource-preview sheets must exist and be human-approved with review evidence;
- `reviewStatus` must be `approved`;
- `reviewedBy` must identify a human/user reviewer;
- `reviewType` must be one of the allowed human-review types;
- AI/model self-approval is forbidden;
- review evidence files must exist;
- transparent isolated assets must pass pixel alpha heuristics.

At `sheet_slicing` and later:

- `reports/cut_report.json` must exist for `approved_sheet_slice` assets;
- each sliced asset must record the exact source file, crop, output, derivation mode, and hashes;
- exact crops are pixel-compared against the declared approved sheet;
- deterministic transforms must freeze the processor script and hash.

Additional blocking codes:

- `asset_isolation_reviewer_missing`
- `asset_isolation_review_type_invalid`
- `asset_isolation_ai_self_approval_forbidden`
- `asset_isolation_review_missing`

## Required reports

```text
reports/asset_isolation_report.json
reports/asset_isolation_report.md
reports/asset_isolation_review.md
reports/cut_report.json
```

The automated report covers structural declarations, approved-design reuse, crop-plan contradictions, file existence, and alpha heuristics. The human review must inspect the contact sheet and confirm that assets contain no neighboring pixels, baked dynamic content, duplicated XML content, dirty alpha edges, or full-screen UI embedded in a background.

## Required command

```bash
python scripts/validate_asset_isolation.py \
  --root UIProduction \
  --stage xml_generation \
  --xml-dir UIProduction/fgui_xml/<package_name> \
  --out UIProduction/reports/asset_isolation_report.json \
  --report-md UIProduction/reports/asset_isolation_report.md
```

A pipeline, XML readiness report, or XML validation report cannot be PASS when asset isolation is required and this validator fails.
