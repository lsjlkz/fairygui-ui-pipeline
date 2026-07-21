# Semantic Controller Mapping Contract

Use this contract whenever requirements, UI/UX design documents, and an approved full-screen design are converted into FairyGUI layout and assembly plans.

## External Instance Override Rule

Treat external Button/Label parameters as per-instance configuration:

```xml
<component src="btn01" fileName="btn_action.xml">
  <Button title="@ui_enter_stage" icon="ui://packageidresourceid"/>
</component>
```

Record requirement-visible title/icon overrides in the `fgui_spec.md` External Component Parameters table. Validate target `extention`, allowed attributes, localization keys, and every `ui://` resource. Do not use a static override for continuously changing runtime values or as a substitute for Controller/Gear state modeling.

## Core Rule

Do not decide Controller, Gear, or runtime ownership from the design image alone.

The required evidence chain is:

```text
requirement documents
+ UI/UX design documents
+ approved design image
+ design_approval.json
-> ui_spec.md State Matrix
-> uxui_semantic_spec.md
-> component_state_map.json
-> layout_spec.json
-> fgui_spec.md Controllers / Gear Mapping
-> component XML controllers / gears
```

A visual difference is not automatically a new component. First determine whether it is:

- the same reusable component in a different discrete state
- continuous runtime data
- a separate semantic component
- static decoration

## Ownership Decision

Use one of these runtime owners:

- `FGUI`: visual state can be fully represented by FairyGUI Controller/Gear.
- `GameUI`: runtime UI code updates content or presentation directly.
- `GamePlay`: gameplay state is the source of truth; UI only reflects it.
- `Config`: configuration determines the state or variant.
- `Mixed`: gameplay/config owns the business state, while FGUI owns discrete visual presentation and GameUI binds dynamic data.
- `None`: explicitly no owner for that responsibility, such as no continuous dynamic data.

For stateful components, record these responsibilities separately when applicable:

- `businessStateOwner`
- `visualStateOwner`
- `dynamicDataOwner`

Recommended pattern:

```json
{
  "componentType": "EquipmentSlot",
  "runtimeOwner": "Mixed",
  "businessStateOwner": "GamePlay",
  "visualStateOwner": "FGUI",
  "dynamicDataOwner": "GameUI"
}
```

## Controller Decision Rules

Use an FGUI Controller when the same component has a finite set of discrete visual states, such as:

- button: normal, pressed, disabled, selected
- equipment: idle, cooking, ready, overcooked, locked
- plate: empty, occupied, completed
- customer: waiting, happy, angry, served
- tab: selected, unselected
- popup: normal, success, failure

Do not model continuous runtime values as many Controller pages:

- countdown values
- progress from 0 to 100
- currency and item counts
- dynamic list contents
- player or customer names
- cooldown values

These belong to GameUI/runtime binding, while a Controller may still represent coarse states such as `idle`, `running`, and `complete`.

Static backgrounds, borders, shadows, and single-state decorations do not require a Controller unless a requirement explicitly gives them states.

## ui_spec.md Requirements

The `State Matrix` must include:

| Component | States | Trigger | Visual Change | Image Needed | Controller | Business Owner | Visual Owner | Dynamic Data Owner | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|

Rules:

- `States` must list all requirement-defined discrete states.
- `Controller` must be an explicit controller name or `none`.
- A stateful component with `Visual Owner=FGUI` or `Mixed` must not use `Controller=none`.
- Continuous data must be described under `Dynamic Data Owner`, not converted into controller pages.
- `Requirement IDs` must trace each state row back to requirement/design-document clauses.

## component_state_map.json Requirements

Top-level source fields are mandatory:

- `requirementSources`: requirement documents or conversation records.
- `designDocumentSources`: UI/UX design documents such as `visual_design_brief.md`.
- `designSources`: the exact approved full-screen design image.

`uxui_semantic_spec.md` must explicitly name every declared source.

Every component must contain:

- `componentType`
- `fguiComponent`
- `purpose`
- `runtimeOwner`
- `businessStateOwner`: required; use `None` when no business transition owner exists.
- `visualStateOwner`: required.
- `dynamicDataOwner`: required; use `None` when the component has no continuous runtime data.
- `states`
- `controllers`
- `reusable`
- `requirementIds`

Every visual instance must follow `references/component-instance-configuration-contract.md` and contain:

- `instanceId`
- `componentType`
- `xmlInstanceName`
- `stateVariant`
- `controllerPages` when discrete Controller state participates
- `implementation.configurationMode`
- `implementation.componentFile`
- `implementation.previewValues`
- `implementation.runtimeBindings`
- `requirementIds`

A reusable component may have a correct Controller/Gear implementation while every parent instance still displays the same default page. Therefore, semantically different reusable instances must use an explicit variant component, supported extension override, editor-verified Controller-page encoding, or runtime binding with a readable preview fallback. `static_default` is forbidden when instance signatures differ.

Every state group must contain:

- `componentType`
- `stateName`
- `trigger`
- `visualDifference`
- `runtimeData`
- `fguiController`
- `gearType`
- `requirementIds`

Rules:

- every `stateName` must exist in the component's `states`
- every `fguiController` must exist in the component's `controllers`
- `FGUI` and `Mixed` visual ownership requires at least one controller for multi-state components
- every requirement-defined state must be represented or explicitly marked runtime-only
- every `gearType` must be one of the supported FairyGUI gear tags

Supported gear types:

- `gearDisplay`
- `gearXY`
- `gearSize`
- `gearLook`
- `gearColor`
- `gearAnimation`
- `gearText`
- `gearIcon`
- `gearDisplay2`
- `gearFontSize`

## layout_spec.json Requirements

Every non-decoration object or slot must link to semantic output:

- `semanticId`
- `componentType`
- `instanceId`
- `stateVariant`
- `stateOwner`
- `runtimeRole`
- `requirementIds`

Rules:

- `componentType` must resolve to `component_state_map.json`
- `stateVariant` must exist in the component's allowed states
- `stateOwner` must be compatible with the semantic runtime/visual owner
- a stateful semantic component must not be flattened into unrelated static images
- objects controlled by FGUI states should normally use `nodeType=component` or an explicitly documented child-gear strategy

## fgui_spec.md Requirements

The following tables are mandatory for stateful screens.

### Controllers

| Component | Controller | Pages | Default | Used By | Requirement IDs | State Owner |
|---|---|---|---|---|---|---|

### Gear Mapping Table

| Component | Controller | Page | Gear Target | Gear Type | Result | Requirement IDs |
|---|---|---|---|---|---|---|

### Instance Configuration

| Instance ID | XML Name | Component Type | Component File | Configuration Mode | Controller Pages | Extension Parameters | Preview Values | Runtime Bindings | Requirement IDs |
|---|---|---|---|---|---|---|---|---|---|

Rules:

- every semantic controller must exist in the Controllers table
- Controllers table pages must cover all semantic states assigned to that controller
- default page must be one of the controller pages
- every gear mapping controller/page must resolve to the Controllers table
- every semantic `stateGroup.gearType` must have a corresponding Gear Mapping row
- components with runtime-only state must explicitly say `Controller=none` and identify their runtime binding owner
- every `visualInstances` entry must appear exactly once in Instance Configuration
- the instance component file and configuration mode must match `component_state_map.json`
- readable preview values are required when runtime code or localization normally fills content

## XML Requirements

When XML exists:

- every planned controller must appear in the owning component XML
- every planned gear type must appear on the expected target object
- every semantic visual instance must resolve to exactly one parent XML component instance by `xmlInstanceName`
- `variant_component` files must have default selected Controller pages matching the declared instance `controllerPages`
- extension override nodes must match the declared per-instance parameters
- approved-design preview components must not display raw localization keys as visible text
- every gear controller reference must resolve to a controller in the same component
- gear pages must belong to the referenced controller
- missing controller/gear implementation is a hard error in `fresh` mode

## Blocking Policy

Before layout analysis, block when:

- requirement or design-document state definitions were not incorporated
- a visible stateful component has no semantic component mapping
- state ownership is missing or ambiguous

Before FairyGUI assembly, block when:

- semantic controllers are not represented in `fgui_spec.md`
- controller pages do not cover the semantic states
- required Gear mappings are absent

Before XML generation, block when:

- `scripts/validate_semantic_controller_mapping.py` fails
- XML Controller/Gear implementation disagrees with the semantic and assembly specifications
- semantically different reusable instances all use an unconfigured default component
- any instance component file, default Controller page, external parameter, preview value, or runtime-binding declaration is missing or inconsistent
- the FairyGUI preview still contains raw localization keys, blank controls, white placeholders, or unintended duplicated default content

## Required Validator

Run:

```bash
python scripts/validate_semantic_controller_mapping.py \
  --root UIProduction \
  --stage xml_generation \
  --out UIProduction/reports/semantic_controller_mapping_report.json \
  --report-md UIProduction/reports/semantic_controller_mapping_report.md
```

When XML already exists, add:

```bash
--xml-dir UIProduction/fgui_xml/<package_name>
```
