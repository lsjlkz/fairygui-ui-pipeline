# Component Reuse And Parameterization Contract

Use this contract before creating FairyGUI component files whenever multiple visible objects share substantially the same structure.

## Purpose

The pipeline must prefer one reusable component plus instance parameters over multiple near-identical XML files.

This contract prevents failures such as:

- two panel frames are split into separate XML files only because their titles differ
- every stat row receives its own XML even though only icon and value differ
- one hero-card XML is created per character even though the hierarchy is identical
- one upgrade-card XML is created per upgrade type even though only text, icon, color, value, or Controller page differs
- preview variants become permanent package resources although the base component can express the differences

The contract is generic. It does not contain fixed component names, title values, character roles, item types, or game-specific enums.

## Reuse Decision Order

Before creating a new component XML, evaluate the candidate in this order:

1. Can an existing component express the difference through external `Button` or `Label` parameters?
2. Can it express the difference through Controller/Gear pages, with the reusable Controller exported and the parent instance passing `controller="name,pageIndex"`?
3. Can runtime binding set the differing text, icon, Loader URL, number, or selected state while retaining a readable editor preview?
4. Can a reusable child component represent the repeated substructure?
5. Only when the node hierarchy or behavior is materially different may a separate variant component be created.

Differences in these values alone are not structural differences:

- title or other text
- icon, selected icon, portrait, badge, or Loader URL
- number or progress value
- color, alpha, enabled state, selected state, or default Controller page
- coordinates or size that can be handled by relations, layout, or instance sizing
- localization key
- runtime binding field

## Required `reusePlan`

Every component with `reusable=true` in `component_state_map.json.components` must include:

```json
{
  "componentType": "ExampleItem",
  "reusable": true,
  "reusePlan": {
    "strategy": "single_component",
    "baseComponentFile": "example_item.xml",
    "extension": "Label",
    "parameterizableFields": [
      "Label.title",
      "Label.icon"
    ],
    "childComponentFiles": [],
    "variantReasons": []
  }
}
```

Required fields:

- `strategy`
- `baseComponentFile`
- `extension`: `Button`, `Label`, or `none`
- `parameterizableFields`: project-defined parameter paths
- `childComponentFiles`: reusable child component files, or an empty array
- `variantReasons`: allowed reasons for separate component files, or an empty array

## Strategies

### `single_component`

Use one XML file for all semantic instances.

Choose this when instances share the same hierarchy and differ only by parameters, runtime values, Controller pages, or layout size.

Allowed instance modes:

- `extension_override`
- `controller_pages`
- `runtime_binding`
- `static_default` when instances are intentionally identical

`variant_component` is forbidden.

### `composite_component`

Use one parent component composed from reusable child components.

Choose this when the component contains repeated parameterized rows, badges, slots, labels, buttons, stat items, or other reusable substructures.

The plan must declare non-empty `childComponentFiles`. The base XML must reference every declared child component. Each declared child file must also belong to its own `reusable=true` component entry with an independent `reusePlan`, so its extension and parameter fields can be validated.

`variant_component` is forbidden unless the reuse plan is changed to `variant_allowed` with a valid reason.

### `variant_allowed`

Use separate XML files only when a material structural or verified platform/editor difference prevents one component from expressing the design.

Every visual instance that uses a file other than `baseComponentFile` must contain:

```json
{
  "implementation": {
    "configurationMode": "variant_component",
    "componentFile": "example_special.xml",
    "variantJustification": {
      "reason": "structural_difference",
      "structuralDifferences": [
        "The special variant contains an additional interactive child list."
      ]
    }
  }
}
```

Allowed reasons:

- `structural_difference`
- `verified_editor_limitation`
- `package_compatibility`
- `temporary_preview_only`

`temporary_preview_only` must also declare `retireAfterEditorValidation=true`.

A difference in title, icon, portrait, number, color, dimensions, default Controller page, or runtime value is not a valid structural justification.

### `unique_component`

Use when the component has one semantic instance and is not intended for reuse. Components marked `reusable=true` must not use this strategy.

## Parameterizable Fields

Parameter paths are project-defined but must describe how instance differences are supplied. Recommended forms:

- `Button.title`
- `Button.icon`
- `Label.title`
- `Label.icon`
- `controller.state`
- `runtime.heroName`
- `runtime.portraitUrl`
- `slot.primaryStat.icon`
- `slot.primaryStat.value`

For `extension_override`, every emitted external attribute must be declared in `parameterizableFields` using `<Extension>.<attribute>`.

For `controller_pages`, `parameterizableFields` must include `controller.<name>`, the target XML Controller must have `exported="true"`, `implementation.controllerParameters` must declare the page name, and the parent XML must pass the resolved page index through `controller="name,index"`.

For `runtime_binding`, `previewValues` must remain readable and `runtimeBindings` must identify the changing fields.

## Recommended Generic Patterns

### Titled Section Frame

Use one `extention="Label"` component for panel frame, background, title plate, and decoration. Different parent instances set only the title and instance size:

```xml
<component name="section_a" src="frame1" fileName="section_frame.xml" size="480,240">
  <Label title="SECTION A" titleFontSize="24"/>
</component>
```

The base component must use relations for stretchable frame/background nodes. A different title or height does not justify another XML file.

### Icon And Value Row

Use one `extention="Label"` child component whose internal objects are named `icon` and `title`:

```xml
<component name="value_row_1" src="row01" fileName="icon_value_row.xml">
  <Label icon="ui://qdf53qpkico01" title="24"/>
</component>
```

Use this pattern for any stable icon-plus-value or icon-plus-title substructure. The project decides the semantic meaning of the icon and value.

### Composite Information Card

Use one parent base component containing reusable child rows, a portrait Loader, optional badge Loader, and text objects. Instance content is supplied through child Label parameters, Controller pages, or runtime bindings. Do not create one parent XML per content identity when the hierarchy remains the same.

## Reusable Child Components

Repeated substructures should become child components when they have a stable internal hierarchy and instance-level content.

A reusable child component should normally expose:

- `Label.title` and `Label.icon` for a title/value plus icon pattern
- `Button.title` and `Button.icon` for an actionable title plus icon pattern
- Controller pages for finite visual states
- runtime bindings for continuous data

The parent component remains responsible for placement and composition. The child component remains responsible for its internal visual structure.

## Required `fgui_spec.md` Table

```markdown
## Component Reuse Plan

| Component Type | Strategy | Base Component File | Extension | Parameterizable Fields | Child Components | Variant Reasons | Requirement IDs |
|---|---|---|---|---|---|---|---|
```

Every reusable semantic component must appear exactly once.

## XML Structural Duplicate Detection

During `xml_generation`, the validator computes both a named structural signature and a hierarchy-only signature for component XML files used by the same semantic component type.

The named signature preserves:

- XML tag hierarchy
- object names
- extension type
- Controller names/pages
- child component structure

The hierarchy-only signature ignores object-name differences so a generator cannot evade reuse by renaming equivalent nodes. Both signatures ignore data-only differences such as:

- IDs
- positions and sizes
- text values
- colors and alpha
- resource URLs and `src`
- selected Controller page
- runtime preview values

Rules:

- identical named signatures or identical hierarchy-only signatures across separate variant files are a hard error
- highly similar signatures are a review warning
- a hard error cannot be waived merely by writing `structural_difference`; the XML must actually differ structurally

Error code:

```text
duplicate_variant_structure_should_reuse_base
```

## Blocking Rules

Block downstream work when:

- a reusable component has no `reusePlan`
- `single_component` or `composite_component` instances use separate variant files
- an extension override contains a field not declared in `parameterizableFields`
- a reusable Controller can express the instance difference but separate component XML files are still created
- `controller_pages` lacks `controllerParameters`, uses a non-exported Controller, references a variant instead of the base file, or emits an incorrect `controller="name,pageIndex"` value
- a variant file has no valid `variantJustification`
- `structural_difference` has no concrete `structuralDifferences`
- `temporary_preview_only` lacks `retireAfterEditorValidation=true`
- a composite child file has no independent reusable component entry and `reusePlan`
- a composite base component does not reference its declared reusable children
- multiple semantic component types claim the same base component file without an explicit wrapper distinction
- two separate variant files have identical normalized XML structure
- the Component Reuse Plan table is missing or inconsistent

## Report

Write:

```text
reports/component_reuse_report.json
reports/component_reuse_report.md
```

Run:

```bash
python scripts/validate_component_reuse.py \
  --root UIProduction \
  --stage xml_generation \
  --xml-dir UIProduction/fgui_xml/<package_name> \
  --out UIProduction/reports/component_reuse_report.json \
  --report-md UIProduction/reports/component_reuse_report.md
```

A passing report proves reuse planning and XML structure consistency. It does not replace FairyGUI editor preview and interaction validation.
