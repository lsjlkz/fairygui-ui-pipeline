# Component Instance Configuration Contract

Use this contract whenever one FairyGUI component resource is reused by multiple semantic instances.

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
    "configurationMode": "variant_component",
    "componentFile": "hero_card_healer.xml",
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

## Allowed Configuration Modes

### `variant_component`

Use a separate registered component XML whose defaults already match the approved design preview.

Use this when:

- instance Controller initialization syntax has not been verified against FairyGUI Editor
- instances require clearly different default pages
- editor preview must match before runtime code executes
- the component has substantial per-instance visual differences

The parent XML `fileName` must equal `implementation.componentFile`, and the variant component's selected Controller pages must match `controllerPages`.

### `extension_override`

Use a matching external extension node such as:

```xml
<component name="restart" src="abs2j" fileName="action_button_secondary_v2.xml">
  <Button title="RESTART" titleFontSize="20"/>
</component>
```

Only use this for supported extension parameters such as Button/Label title and icon overrides. It does not replace Controller initialization for role, state, or selection differences.

### `controller_pages`

Use one component file and encode selected Controller pages on the instance.

This mode is allowed only when the exact XML representation has been verified by FairyGUI Editor and the validator can parse it. Do not invent a `controller` attribute format from memory.

### `runtime_binding`

Use runtime code to set instance data and states.

This requires:

- non-empty `runtimeBindings`
- non-empty `previewValues`
- an editor-preview fallback that already resembles the approved design
- an explicit note that runtime binding occurs after construction

Runtime binding alone is not acceptable when all instances look identical or blank in the FairyGUI review screenshot.

### `static_default`

Use only when the component has one semantic instance, or every instance intentionally shares the same configuration and preview.

It is forbidden for multiple reusable instances whose role, Controller pages, title, icon, state, or preview values differ.

## Required `fgui_spec.md` Table

```markdown
## Instance Configuration

| Instance ID | XML Name | Component Type | Component File | Configuration Mode | Controller Pages | Extension Parameters | Preview Values | Runtime Bindings | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|
```

Every `visualInstances` entry must have exactly one matching row.

## XML Validation

For every visual instance, validation must:

1. Find exactly one parent XML component instance by `xmlInstanceName`.
2. Resolve its `src` through `package.xml`.
3. Require `fileName` to match `implementation.componentFile`.
4. For `variant_component`, parse the target XML and verify selected Controller pages.
5. For `extension_override`, validate child tag, attributes, target `extention`, and all `ui://` values.
6. For `controller_pages`, verify the editor-confirmed instance encoding.
7. For approved-design previews, reject raw localization keys displayed as visible text when `previewValues` provide readable text.
8. Reject multiple semantically different reusable instances that all use an unconfigured default component.

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
5. record the result in `reports/fgui_visual_review.md`

The package remains `draft_unverified` until this review passes.
