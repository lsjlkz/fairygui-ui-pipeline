# Output Templates

## ui_spec.md

```md
# [screen_name] UX/UI Spec

## Confirmed Information

## Temporary Assumptions

## Open Questions

## Out of Scope

## Screen Goal

## Player Flow

## Layout Regions

| Region | Purpose | Position | Notes |
|---|---|---|---|

## Components

| Name | Type | Operation | States | Binding |
|---|---|---|---|---|

## State Matrix

| Component | States | Trigger | Visual Change | Image Needed | Controller | Business Owner | Visual Owner | Dynamic Data Owner | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|

## Art Direction

## Visual References

| File | Role | Primary | Allowed Uses | Resolution |
|---|---|---|---|---|

## Asset Requirements

| Asset | Use | Source Pixel Size | Display Size | Scale Policy | Transparent | Sheet | FairyGUI Mapping |
|---|---|---:|---:|---|---|---|---|

## Acceptance Criteria
```

## visual_design_brief.md

```md
# [screen_name] Visual Design Brief

## Confirmed Requirement Sources

## Screen Goal

## Design Resolution

## Primary Reference And Allowed Uses

| File | Role | Allowed Uses | Must Follow | Must Not Copy |
|---|---|---|---|---|

## Functional Region Map

| Region | Purpose | Required Content | Interaction Space | Priority |
|---|---|---|---|---|

## Required Components And States

| Component | Required States | Visible In Mockup | Production Separation Rule |
|---|---|---|---|

## Visual Hierarchy

## Art Direction

## Text And Localization Policy

## Asset Separation Constraints

## Negative Constraints

## Mockup Acceptance Criteria

## Known Risks
```

## design_draft_review.md

```md
# Design Draft Review

## Draft
- file:
- resolution:

## Requirement Coverage

| Requirement / Region | Covered | Notes |
|---|---|---|

## Visual Review

- composition:
- hierarchy:
- style consistency:
- perspective and lighting:
- interaction-space clarity:
- text-baking violations:
- production-separation risks:

## Blocking Issues

## Decision
- status: pending
- nextAction: request_user_confirmation
```

## design_approval.json

Pending record created by the pipeline before user confirmation:

```json
{
  "version": "0.1.0",
  "status": "pending",
  "candidateFile": "generated/design/screen_design_draft_v1.png",
  "approvedFile": null,
  "approvedFileSha256": null,
  "resolution": [1920, 1080],
  "approvedFor": [],
  "confirmation": null,
  "knownDeviations": [],
  "reviewNotes": [],
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

Record after explicit confirmation of the exact file:

```json
{
  "version": "0.1.0",
  "status": "approved",
  "candidateFile": "generated/design/screen_design_final.png",
  "approvedFile": "generated/design/screen_design_final.png",
  "approvedFileSha256": "<exact-file-sha256>",
  "resolution": [1920, 1080],
  "approvedFor": [
    "semantic_analysis",
    "layout_analysis",
    "asset_planning",
    "resource_generation",
    "fairygui_assembly",
    "xml_generation"
  ],
  "confirmation": {
    "type": "user_confirmation",
    "recordedBy": "user",
    "note": "The user explicitly approved this exact design file.",
    "confirmedAt": "2026-01-01T00:00:00Z"
  },
  "knownDeviations": [],
  "reviewNotes": [],
  "updatedAt": "2026-01-01T00:00:00Z"
}
```

## design_gate_report.json

```json
{
  "approved": true,
  "checkedAt": "2026-01-01T00:00:00Z",
  "root": "UIProduction",
  "stage": "semantic_analysis",
  "approvedFile": "UIProduction/generated/design/screen_design_final.png",
  "approvedFileSha256": "<exact-file-sha256>",
  "blockers": [],
  "warnings": []
}
```

## uxui_semantic_spec.md

```md
# [screen_name] UX/UI Semantic Spec

## Sources

### Requirement Sources
- specs/ui_spec.md

### UI/UX Design Document Sources
- specs/visual_design_brief.md

### Approved Design Sources
- generated/design/screen_design_final.png

## Screen Goal And User Flow

## UI Part Inventory

| Semantic ID | Visible Part | Purpose | Component Type | Requirement IDs |
|---|---|---|---|---|

## State Ownership

| Component Type | Business Owner | Visual Owner | Dynamic Data Owner | Controller Decision | Requirement IDs |
|---|---|---|---|---|---|

## Component Reuse

## Interaction Model

## Requirement / Design Mismatch Report

## Blocking Questions
```

## component_state_map.json

```json
{
  "version": "0.1.0",
  "screen": "screen_name",
  "requirementSources": ["specs/ui_spec.md"],
  "designDocumentSources": ["specs/visual_design_brief.md"],
  "designSources": ["generated/design/screen_design_final.png"],
  "components": [
    {
      "componentType": "EquipmentSlot",
      "fguiComponent": "equipment_slot",
      "purpose": "Display and operate one cooking device",
      "runtimeOwner": "Mixed",
      "businessStateOwner": "GamePlay",
      "visualStateOwner": "FGUI",
      "dynamicDataOwner": "GameUI",
      "states": ["idle", "cooking", "ready", "overcooked"],
      "controllers": ["state"],
      "reusable": true,
      "reusePlan": {
        "strategy": "single_component",
        "baseComponentFile": "equipment_slot.xml",
        "extension": "none",
        "parameterizableFields": [
          "controller.state",
          "runtime.foodId",
          "runtime.cookProgress"
        ],
        "childComponentFiles": [],
        "variantReasons": []
      },
      "requirementIds": ["REQ-EQUIPMENT-STATE"]
    }
  ],
  "visualInstances": [
    {
      "instanceId": "equipment_slot_left_01",
      "componentType": "EquipmentSlot",
      "xmlInstanceName": "equipment_slot_left",
      "stateVariant": "ready",
      "controllerPages": {
        "state": "ready"
      },
      "slotRole": "cook_source",
      "requirementIds": ["REQ-EQUIPMENT-STATE"],
      "implementation": {
        "configurationMode": "controller_pages",
        "componentFile": "equipment_slot.xml",
        "controllerParameters": {
          "state": "ready"
        },
        "previewValues": {
          "title": "READY",
          "food": "preview_food"
        },
        "runtimeBindings": ["foodId", "cookProgress", "state"]
      }
    }
  ],
  "stateGroups": [
    {
      "componentType": "EquipmentSlot",
      "stateName": "ready",
      "trigger": "cook_timer_completed",
      "visualDifference": "ready food and highlight are visible",
      "runtimeData": ["foodId", "cookProgress"],
      "fguiController": "state",
      "gearType": ["gearDisplay", "gearIcon"],
      "requirementIds": ["REQ-EQUIPMENT-STATE"]
    }
  ],
  "requirementLinks": [],
  "reviewStatus": "reviewed",
  "blockingForLayout": false,
  "blockingForXml": false
}
```

## component_visual_parts.json

```json
{
  "version": "0.1.0",
  "screen": "screen_name",
  "designSources": ["generated/design/screen_design_final.png"],
  "components": [
    {
      "componentType": "ExampleCard",
      "componentFiles": ["example_card.xml"],
      "requirementIds": ["REQ-EXAMPLE"],
      "parts": [
        {
          "partId": "frame",
          "role": "background_frame",
          "required": true,
          "visibleInApprovedDesign": true,
          "visualImportance": "structural",
          "complexity": "detailed",
          "requirementIds": ["REQ-EXAMPLE"],
          "implementation": {
            "mode": "asset_image",
            "assetName": "frame_example_card",
            "xmlNodeNames": ["frame"],
            "appliesToFiles": ["example_card.xml"],
            "nodeMatch": "all",
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

## layout_spec.json

```json
{
  "version": "0.1.0",
  "screen": "screen_name",
  "designResolution": [1920, 1080],
  "sourceImages": ["generated/design/screen_design_final.png"],
  "coordinateSystem": {
    "origin": "top_left",
    "unit": "px",
    "space": "design_resolution"
  },
  "regions": [],
  "objects": [
    {
      "name": "equipment_slot_left",
      "semanticId": "equipment.slot",
      "instanceId": "equipment_slot_left_01",
      "componentType": "EquipmentSlot",
      "stateVariant": "idle",
      "nodeType": "component",
      "component": "equipment_slot",
      "region": "work_area",
      "bbox": [100, 200, 320, 280],
      "binding": "equipmentSlotLeft",
      "stateOwner": "FGUI",
      "runtimeRole": "cook_source",
      "zLayer": "content",
      "occlusionPolicy": "normal",
      "requirementIds": ["REQ-EQUIPMENT-STATE"],
      "slicePolicy": "use_component"
    }
  ],
  "slots": [],
  "relations": [],
  "reviewStatus": "needs_overlay_review",
  "blockingForXml": true
}
```

## slice_plan.json

```json
{
  "version": "0.1.0",
  "screen": "screen_name",
  "sourceLayout": "specs/layout_spec.json",
  "sourceImages": [],
  "rules": {
    "doNotSliceDynamicStatesFromFlatDesign": true,
    "requireOverlayReviewBeforeXml": true
  },
  "slices": []
}
```

## asset_manifest.json visual and size fields

```json
{
  "package": {
    "name": "cooking",
    "outputPath": "fgui_xml/cooking"
  },
  "production": {
    "generateFullScreenDesign": true,
    "requiresDesignApproval": true,
    "requiresVisualPartCoverage": true,
    "generateVisualAssets": true,
    "requiresVisualReference": true
  },
  "referenceImages": [
    {
      "file": "references/ui_reference.png",
      "role": "style_and_layout",
      "resolution": [1920, 1080],
      "isPrimary": true,
      "allowedUses": ["style", "layout", "asset_generation"]
    }
  ],
  "assets": [
    {
      "name": "bg_main",
      "file": "fgui_xml/cooking/art/bg_main.png",
      "packageRelativeFile": "art/bg_main.png",
      "sourcePixelSize": [1920, 1080],
      "displaySize": [1920, 1080],
      "scalePolicy": "pixel_exact",
      "renderMode": "normal",
      "nineSliceGrid": null,
      "assetSource": {
        "mode": "provided_bitmap",
        "sourceFile": "references/ui_reference.png",
        "reviewStatus": "approved"
      }
    }
  ]
}
```

## sheet_plan.md

```md
# Sheet Plan

## Global Rules

- naming: lowercase snake_case
- isolated assets: transparent png
- text: not baked into images
- one item per cell

## Sheets

| Sheet | Rows | Cols | Cell Size | Assets |
|---|---:|---:|---:|---|

## Imagegen Prompt Batches

### [sheet_name]

Positive prompt:

Negative constraints:

Cell list:
```

## fgui_spec.md

```md
# FairyGUI Assembly Spec

## Package

| Field | Value |
|---|---|
| package name | |
| package id | |
| design resolution | |

## Components

| Component | File | Extension | Exported | Purpose |
|---|---|---|---|---|

## Display List

Rows are ordered back-to-front. Opaque backgrounds use the smallest order and must appear first in XML.

| Parent | Order | Name | Node Type | Asset Name | Resource | Position | Size | Size Source | Z Layer | Occlusion Policy | Binding |
|---|---:|---|---|---|---|---|---|---|---|---|---|

## Layout Region Table

| Region | Parent | Bounds | Anchor / Relation | Type | Interaction Responsibility |
|---|---|---|---|---|---|

## Slot Table

| Slot | Component Name | Region | XY | Size | Pivot | Binding | State Owner |
|---|---|---|---|---|---|---|---|

## Component Ownership Table

| Responsibility | Owner Component | Should Not Live In |
|---|---|---|

## Component Reuse Plan

| Component Type | Strategy | Base Component File | Extension | Parameterizable Fields | Child Components | Variant Reasons | Requirement IDs |
|---|---|---|---|---|---|---|---|

## Controllers

Set `Exported=true` only when a parent component instance passes that Controller through its `controller="name,pageIndex"` attribute.

| Component | Controller | Pages | Default | Exported | Used By | Requirement IDs | State Owner |
|---|---|---|---|---|---|---|---|

## Gear Mapping Table

| Component | Controller | Page | Gear Target | Gear Type | Result | Requirement IDs |
|---|---|---|---|---|---|---|

## Visual Part Coverage

| Component Type | Part ID | Role | Required | Importance | Complexity | Implementation Mode | Asset Name | XML Nodes | Applies To Files | Fallback Policy | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|---|---|

## Transitions

| Component | Transition | Trigger | Draft Behavior | Needs Editor Review |
|---|---|---|---|---|

## Relations

## Instance Configuration

Use this table for every `component_state_map.visualInstances` entry. Different reusable instances must declare how their Controller pages, titles, icons, preview values, and runtime bindings are materialized.

| Instance ID | XML Name | Component Type | Component File | Configuration Mode | Controller Pages | Controller Parameters | Extension Parameters | Preview Values | Runtime Bindings | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|---|

## External Component Parameters

Use this table whenever a parent component instance contains an external `<Button .../>` or `<Label .../>` parameter node. The target component's root `extention`, allowed attributes, localization keys, and all referenced `ui://` URLs must be validated.

| Parent Component | Instance | Target Component | Extension | Title Override | Icon Override | Selected Override | Localization Key | Validation Status |
|---|---|---|---|---|---|---|---|---|

## Unity Bindings

| Field | Type | FairyGUI Path | Notes |
|---|---|---|---|

## Automation Risks
```

## semantic_controller_mapping_report.json

```json
{
  "ok": true,
  "checkedAt": "2026-01-01T00:00:00Z",
  "root": "UIProduction",
  "stage": "xml_generation",
  "xmlDir": null,
  "errors": [],
  "warnings": [],
  "summary": {
    "components": 4,
    "stateGroups": 12,
    "visualInstances": 8,
    "controllers": 4,
    "gearMappings": 18,
    "instanceConfigurations": 8
  }
}
```

## component_reuse_report.json

```json
{
  "ok": true,
  "checkedAt": "2026-01-01T00:00:00Z",
  "root": "UIProduction",
  "stage": "xml_generation",
  "xmlDir": "UIProduction/fgui_xml/package_name",
  "errors": [],
  "warnings": [],
  "summary": {
    "reusableComponents": 4,
    "visualInstances": 8,
    "variantFiles": 0
  }
}
```

## display_list_z_order_report.json

```json
{
  "ok": true,
  "checkedAt": "2026-01-01T00:00:00Z",
  "root": "UIProduction",
  "stage": "xml_generation",
  "xmlDir": "UIProduction/fgui_xml/package_name",
  "errors": [],
  "warnings": [],
  "summary": {
    "parents": 3,
    "plannedNodes": 18,
    "xmlChecked": true
  }
}
```

## bitmap_asset_provenance_report.json

```json
{
  "ok": true,
  "checkedAt": "2026-01-01T00:00:00Z",
  "root": "UIProduction",
  "stage": "xml_generation",
  "errors": [],
  "warnings": [],
  "summary": {
    "assets": 20,
    "icons": 7,
    "scriptsScanned": 3
  }
}
```

## component_reuse_report.md

```md
# Component Reuse Report

- result: PASS
- stage: xml_generation

## Errors
- none

## Warnings
- none
```

## visual_part_coverage_report.json

```json
{
  "ok": true,
  "checkedAt": "2026-01-01T00:00:00Z",
  "root": "UIProduction",
  "stage": "xml_generation",
  "xmlDir": "UIProduction/fgui_xml/package_name",
  "errors": [],
  "warnings": [],
  "summary": {
    "components": 4,
    "parts": 24,
    "requiredParts": 20
  }
}
```

## visual_part_coverage_report.md

```md
# Visual Part Coverage Report

- result: PASS
- stage: xml_generation

## Errors
- none

## Warnings
- none
```

## semantic_controller_mapping_report.md

```md
# Semantic Controller Mapping Report

- result: PASS
- stage: xml_generation

## Errors

- none

## Warnings

- none
```

## pipeline_stage_timings.json

```json
{
  "version": "0.1.0",
  "runId": "9efc07d8-cc4f-48fb-87c6-fcb4061395d4",
  "pipeline": "fairygui-ui-pipeline",
  "root": "UIProduction",
  "status": "completed",
  "startedAt": "2026-01-01T00:00:00Z",
  "finishedAt": "2026-01-01T00:32:15Z",
  "updatedAt": "2026-01-01T00:32:15Z",
  "stages": [
    {
      "stageNumber": 1,
      "stageId": "requirement_intake",
      "name": "Requirement intake",
      "defaultCategory": "active",
      "status": "completed",
      "attemptCount": 1,
      "durationMs": 125000,
      "attempts": [
        {
          "attempt": 1,
          "status": "completed",
          "category": "active",
          "startedAt": "2026-01-01T00:00:00Z",
          "finishedAt": "2026-01-01T00:02:05Z",
          "durationMs": 125000,
          "notes": [],
          "artifacts": ["specs/ui_spec.md"]
        }
      ]
    }
  ],
  "summary": {
    "wallClockDurationMs": 1935000,
    "activeDurationMs": 1310000,
    "waitingDurationMs": 480000,
    "externalDurationMs": 90000,
    "accountedDurationMs": 1880000,
    "untrackedDurationMs": 55000,
    "stageStatusCounts": {
      "pending": 0,
      "running": 0,
      "completed": 15,
      "skipped": 1,
      "blocked": 0,
      "failed": 0
    },
    "human": {
      "wallClock": "00:32:15.000",
      "active": "00:21:50.000",
      "waiting": "00:08:00.000",
      "external": "00:01:30.000",
      "accounted": "00:31:20.000",
      "untracked": "00:00:55.000"
    }
  }
}
```

The real report contains all 16 canonical stage entries, including skipped stages and every rework attempt.

## pipeline_stage_timings.md

```md
# Pipeline Stage Timing Report

- pipeline: `fairygui-ui-pipeline`
- run ID: `9efc07d8-cc4f-48fb-87c6-fcb4061395d4`
- status: **COMPLETED**
- total wall-clock: **00:32:15.000**
- active processing: **00:21:50.000**
- human waiting: **00:08:00.000**
- external tools: **00:01:30.000**
- untracked/idle: **00:00:55.000**

## Stage Summary

| # | Stage | Category | Status | Attempts | Duration | Started | Finished |
|---:|---|---|---|---:|---:|---|---|
| 1 | `requirement_intake` — Requirement intake | active | completed | 1 | 00:02:05.000 | 2026-01-01T00:00:00Z | 2026-01-01T00:02:05Z |
| 5 | `design_approval` — Explicit human design approval | waiting | completed | 1 | 00:08:00.000 | 2026-01-01T00:07:00Z | 2026-01-01T00:15:00Z |
```

## cut_report.json

```json
{
  "ok": true,
  "sheet": "sheet_food_5x4",
  "checkedAt": "2026-01-01T00:00:00Z",
  "outputs": [
    {
      "name": "food_patty_raw",
      "file": "generated/sliced/food_patty_raw.png",
      "status": "ok",
      "warnings": []
    }
  ],
  "errors": []
}
```

## xml_readiness_report.json

```json
{
  "ready": false,
  "checkedAt": "2026-01-01T00:00:00Z",
  "root": "UIProduction",
  "profile": "fresh",
  "designDriven": true,
  "requireDesignApproval": true,
  "resourceGeneration": true,
  "embeddedDocsIntegrity": true,
  "semanticControllerMapping": true,
  "componentReuse": true,
  "displayListZOrder": true,
  "bitmapAssetProvenance": true,
  "visualPartCoverage": true,
  "designApproved": true,
  "packageName": "cooking",
  "packageId": "qdf53qpk",
  "blockers": [],
  "warnings": []
}
```

## xml_generation_input_snapshot.json

```json
{
  "version": "0.1.0",
  "profile": "fresh",
  "packageName": "cooking",
  "packageId": "qdf53qpk",
  "designResolution": [1920, 1080],
  "sources": {
    "manifest": "manifests/asset_manifest.json",
    "registry": "manifests/fgui_id_registry.json",
    "fguiSpec": "specs/fgui_spec.md",
    "visualDesignBrief": "specs/visual_design_brief.md",
    "designApproval": "reports/design_approval.json",
    "approvedDesign": "generated/design/screen_design_final.png",
    "referenceImage0": "references/ui_reference.png",
    "assetImage0": "fgui_xml/cooking/art/bg_main.png"
  },
  "sourceVersions": {},
  "unresolvedRisks": [],
  "status": "frozen_for_generation"
}
```

## xml_validate_report.json

```json
{
  "ok": true,
  "mode": "fresh",
  "package_name": "cooking",
  "package_id": "qdf53qpk",
  "files_checked": 2,
  "manifest_loaded": true,
  "registry_loaded": true,
  "package_resource_paths_checked": true,
  "component_extension_overrides_checked": true,
  "component_controller_parameters_checked": true,
  "semantic_controller_mapping_checked": true,
  "component_instance_configurations_checked": true,
  "component_reuse_checked": true,
  "display_list_z_order_checked": true,
  "bitmap_asset_provenance_checked": true,
  "visual_part_coverage_checked": true,
  "error_count": 0,
  "warning_count": 0,
  "issues": []
}
```
