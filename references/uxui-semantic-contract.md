# UX/UI Semantic Contract

Use this contract before design-to-layout analysis when requirements and an explicitly approved UI design image are both available.

## Core Rule

Do not treat every visible shape in a design image as a different UI component.

If the image was generated from requirements or design documents, first run `scripts/check_design_approval.py --stage semantic_analysis`. Then map the exact approved design image back to the requirement document:

```text
requirement document
+ approved design image
+ design_approval.json
-> uxui_semantic_spec.md
-> component_state_map.json
-> layout_spec.json
-> slice_plan.json
-> fgui_spec.md
-> XML draft
```

The semantic pass owns meaning, purpose, state, component reuse, and runtime responsibility. The layout pass owns coordinates and spatial hierarchy.

## Required Project Files

Store these in the active project's `UIProduction/<screen>/specs/` directory:

- `uxui_semantic_spec.md`: human-readable screen purpose, user flow, UI part inventory, state model, component reuse, and requirement-to-visual mapping.
- `component_state_map.json`: machine-readable mapping from visual instances to semantic components, states, owners, and runtime responsibilities.

Do not store project-specific semantic maps inside this reusable skill.

## uxui_semantic_spec.md Requirements

Include:

- requirement sources, `design_approval.json`, and the exact approved design image source
- screen goal and player/user flow
- UI part inventory: each visible area, what it is, what it does, and which requirement it supports
- component reuse notes: when multiple visible objects are the same component class in different states or slots
- state model: component, state/page, trigger, visual difference, runtime owner
- ownership split: business state owner, FGUI visual state owner, and dynamic-data owner
- Controller decision: whether discrete states belong to an FGUI Controller, and why
- Gear decision: which visual properties change for each Controller page
- interaction model: click/drag/focus/confirm responsibilities
- content model: static art, runtime text, runtime icon, list item, slot, progress, timer, alert
- mismatch report: design elements not found in requirements, and requirements not visible in design
- blocking questions before XML

## component_state_map.json Requirements

Top-level fields:

- `version`
- `screen`
- `requirementSources`
- `designDocumentSources`
- `designSources`
- `components`
- `visualInstances`
- `stateGroups`
- `requirementLinks`
- `reviewStatus`
- `blockingForLayout`
- `blockingForXml`

Component fields:

- `componentType`: reusable semantic class, for example `CustomerSlot`, `EquipmentSlot`, `PlateSlot`, `IngredientSlot`.
- `fguiComponent`: expected FairyGUI component or template name when known.
- `purpose`
- `runtimeOwner`: `FGUI`, `GameUI`, `GamePlay`, `Config`, or `Mixed`.
- `businessStateOwner`: source of truth for business transitions when applicable.
- `visualStateOwner`: usually `FGUI`, `GameUI`, or `Mixed`.
- `dynamicDataOwner`: owner of continuous values, runtime text/icons, progress, timers, and list contents.
- `states`: allowed states/pages.
- `controllers`: required FGUI controllers, or an empty list only when visual state is runtime-only/static.
- `requirementIds`: requirement/design-document clauses that justify the component and states.
- `reusable`: boolean.

Visual instance fields:

- `instanceId`: unique visible instance in the specific design image.
- `componentType`: reference to a reusable component type.
- `stateVariant`: visible state/page represented by this instance.
- `slotRole`: runtime role, such as `source`, `target`, `preview`, `order`, `progress`, `alert`.
- `designRegionHint`: rough region name before layout bbox is finalized.
- `requirementIds`: requirement references this instance supports.
- `notes`

State group fields:

- `componentType`
- `stateName`
- `trigger`
- `visualDifference`
- `runtimeData`
- `fguiController`
- `gearType`
- `requirementIds`

## Design-To-Layout Dependency

`layout_spec.json` must reference semantic output:

- every `region` should link to a semantic purpose or requirement group
- every `object` should include `semanticId`, `componentType`, `instanceId`, and `stateVariant` when it is not pure decoration
- every `slot` should include `componentType`, `slotRole`, `stateOwner`, and `runtimeRole`

If a design shows two copies of the same component in different states, create two visual instances with the same `componentType` and different `instanceId` / `stateVariant`. Do not create two unrelated component types.

Example:

```json
{
  "visualInstances": [
    {
      "instanceId": "fryer_idle_left",
      "componentType": "EquipmentSlot",
      "stateVariant": "idle",
      "slotRole": "cook_source"
    },
    {
      "instanceId": "fryer_ready_right",
      "componentType": "EquipmentSlot",
      "stateVariant": "ready",
      "slotRole": "cook_source"
    }
  ]
}
```

## Gates

Before semantic analysis:

- the design approval gate must pass for `semantic_analysis` when the screen design was generated by the pipeline
- requirement documents, UI/UX design documents, and the approved image must be recorded separately in `requirementSources`, `designDocumentSources`, and `designSources`
- `uxui_semantic_spec.md` must explicitly name every declared source
- the approved image path and SHA-256 must be recorded

Before layout:

- requirement documents, UI/UX design documents, and the exact approved design image must all be considered
- semantic component reuse must be identified
- obvious visible states and requirement-defined non-visible states must be mapped to component state models
- state ownership must separate business state, visual state, and continuous runtime data
- multi-state components visually owned by `FGUI` or `Mixed` must declare Controller mappings
- run `scripts/validate_semantic_controller_mapping.py --stage layout_analysis`

Before XML:

- `uxui_semantic_spec.md`, `component_state_map.json`, `layout_spec.json`, `slice_plan.json`, `asset_manifest.json`, `fgui_id_registry.json`, and `fgui_spec.md` must agree
- component states must map to controllers/gears or explicit runtime code ownership
- `scripts/validate_semantic_controller_mapping.py --stage xml_generation` must pass
- mismatches must be resolved or recorded as accepted risk
