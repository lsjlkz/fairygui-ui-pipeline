# Component Instance Configuration Contract

Use this contract whenever one FairyGUI component resource is reused by multiple semantic instances. Read `references/component-reuse-parameterization-contract.md` first so instance configuration does not become an excuse to create near-identical variant XML files.

## Core Failure This Contract Prevents

A reusable component may define correct Controllers and Gears while every parent instance still opens on the same default page. This produces structurally valid XML but visually wrong UI, for example:

- swordsman and healer cards both display the swordsman
- two strategy rows both use the same role and choice
- VIT, ATK, and SPD options all display one default icon/title
- primary and secondary actions both use the same button skin/title

Controller/Gear coverage at the component level is therefore not enough. Every semantic instance must have a verifiable configuration strategy.

## Required `visualInstances` Fields

Every item in `component_state_map.json.visualInstances` must include:

```json
{
  "instanceId": "hero_healer_main",
  "componentType": "HeroCard",
  "xmlInstanceName": "hero_healer",
  "stateVariant": "normal",
  "controllerPages": {
    "role": "healer",
    "condition": "normal"
  },
  "implementation": {
    "configurationMode": "controller_pages",
    "componentFile": "hero_card.xml",
    "controllerParameters": {
      "role": "healer"
    },
    "previewValues": {
      "primaryStat": "14",
      "speed": "78"
    },
    "runtimeBindings": ["heroId", "healing", "speed", "portraitUrl"]
  },
  "requirementIds": ["REQ-MAIN-HEROES"]
}
```

Required fields:

- `instanceId`: stable semantic instance ID
- `componentType`: semantic component type
- `xmlInstanceName`: exact parent XML `<component name>` value
- `implementation.configurationMode`
- `implementation.componentFile`
- `implementation.previewValues`
- `implementation.runtimeBindings` when runtime data participates
- `requirementIds`

## Reuse-First Configuration Order

Before choosing a mode, apply this order:

1. `extension_override` for supported Button/Label title and icon parameters.
2. `controller_pages` for verified finite visual-state selection through an exported child Controller and the parent instance `controller` attribute.
3. `runtime_binding` for names, values, portraits, Loader URLs, and other runtime content, with readable preview defaults.
4. reusable child components for repeated substructures such as icon-plus-value rows.
5. `variant_component` only when `reusePlan.strategy=variant_allowed` and the XML structure is materially different.

Differences in title, icon, portrait, number, color, dimensions, selected Controller page, localization key, or runtime value do not justify a separate component XML.

## Allowed Configuration Modes

### `variant_component`

Use a separate registered component XML only as a controlled exception.

Required conditions:

- the semantic component declares `reusePlan.strategy=variant_allowed`
- the variant reason is listed in `reusePlan.variantReasons`
- the instance declares `implementation.variantJustification`
- structural differences are concrete and machine-verifiable when the reason is `structural_difference`
- a temporary preview variant declares `retireAfterEditorValidation=true`

The parent XML `fileName` must equal `implementation.componentFile`, the variant component's selected Controller pages must match `controllerPages`, and `validate_component_reuse.py` must confirm that the variant is not structurally identical to the base component.

### `extension_override`

Use a matching external extension node such as:

```xml
<component name="restart" src="abs2j" fileName="action_button_secondary_v2.xml">
  <Button title="RESTART" titleFontSize="20"/>
</component>
```

Use this preferentially for supported Button/Label title and icon overrides. Every emitted field must be declared in the owning component's `reusePlan.parameterizableFields`. It does not replace Controller initialization for role, state, or selection differences.

### `controller_pages`

Use one component file and expose one finite visual Controller as an external component property.

Verified FairyGUI pattern:

```xml
<!-- reusable child component -->
<controller name="role" exported="true" pages="0,swordsman,1,healer" selected="0"/>
```

```xml
<!-- parent component instance -->
<component name="hero_healer" src="card1" fileName="hero_card.xml" controller="role,1"/>
```

The parent value is `controllerName,pageIndex`, not `controllerName,pageName`. The page index is resolved from the target Controller's `pages` sequence.

Required semantic declaration:

```json
{
  "controllerPages": {"role": "healer"},
  "implementation": {
    "configurationMode": "controller_pages",
    "componentFile": "hero_card.xml",
    "controllerParameters": {"role": "healer"}
  }
}
```

Rules:

- the target Controller must have `exported="true"`
- `reusePlan.parameterizableFields` must contain `controller.role`
- the instance must use the base component file
- `controllerParameters` and `controllerPages` must agree
- the parent XML attribute must exactly equal `role,1` for the example above
- current automation accepts one externally passed Controller per component instance; multiple Controller parameters require a verified FairyGUI Editor export example before support is expanded

### `runtime_binding`

Use runtime code to set instance data and states.

This requires:

- non-empty `runtimeBindings`
- non-empty `previewValues`
- an editor-preview fallback that already resembles the approved design
- an explicit note that runtime binding occurs after construction

Runtime binding alone is not acceptable when all instances look identical or blank in the FairyGUI review screenshot. A composite component should use reusable child components for stable repeated substructures instead of duplicating those rows inside multiple parent variants.

### `static_default`

Use only when the component has one semantic instance, or every instance intentionally shares the same configuration and preview.

It is forbidden for multiple reusable instances whose role, Controller pages, title, icon, state, or preview values differ.

## Required `fgui_spec.md` Table

```markdown
## Instance Configuration

| Instance ID | XML Name | Component Type | Component File | Configuration Mode | Controller Pages | Controller Parameters | Extension Parameters | Preview Values | Runtime Bindings | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|---|
```

Every `visualInstances` entry must have exactly one matching row.

## XML Validation

For every visual instance, validation must:

1. Find exactly one parent XML component instance by `xmlInstanceName`.
2. Resolve its `src` through `package.xml`.
3. Require `fileName` to match `implementation.componentFile`.
4. For `variant_component`, parse the target XML and verify selected Controller pages.
5. For `extension_override`, validate child tag, attributes, target `extention`, and all `ui://` values.
6. For `controller_pages`, require the target Controller `exported="true"`, resolve the declared page name to its page index, and verify the exact parent `controller="name,index"` encoding.
7. For approved-design previews, reject raw localization keys displayed as visible text when `previewValues` provide readable text.
8. Reject multiple semantically different reusable instances that all use an unconfigured default component.
9. Run `validate_component_reuse.py` and reject variant files whose normalized structure is identical to the base or another variant.
10. Verify composite components reference every declared reusable child component.

## Localization Preview Rule

The FairyGUI editor preview must remain readable before project localization code runs.

Recommended:

```xml
<text name="txt_brand" text="TWINBOUND" customData="loc:ui_twinbound_title"/>
```

Avoid using visible `text="@ui_twinbound_title"` in an approved-design preview unless the project has a verified FairyGUI editor localization plugin that resolves it during review.

## Visual Review Gate

Structural XML validation does not prove visual fidelity. After the package opens successfully:

1. capture the FairyGUI preview at the design resolution
2. compare it with the approved full-screen design
3. verify that repeated instances differ as specified
4. verify no raw localization keys, white placeholders, missing titles, duplicate portraits, or duplicate default icons remain
5. verify content-only differences use parameters, Controllers, runtime bindings, or reusable child components instead of duplicate XML files
6. record the result in `reports/fgui_visual_review.md`

The package remains `draft_unverified` until this review passes.
