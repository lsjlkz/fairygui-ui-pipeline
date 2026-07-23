# Display List Z-Order Contract

Use this contract for every FairyGUI component that contains overlapping visual objects or child components.

## Core Rendering Rule

FairyGUI `<displayList>` is ordered from back to front:

- the first child is the lowest/backmost visual
- later children render above earlier children
- a later opaque or nearly opaque full-size object can cover all earlier content and interactions

Therefore, backgrounds must appear near the beginning of `<displayList>`, while intentional frames, overlays, modals, and debug layers appear later only when their transparency and blocking behavior are explicit.

## Required Planning Fields

Every non-asset row in `fgui_spec.md` Display List must contain:

- `Order`: zero-based direct-child order within the parent component
- `Z Layer`: `background`, `content`, `foreground`, `overlay`, `modal`, or `debug`
- `Occlusion Policy`: `opaque_background`, `normal`, `transparent_frame`, `intentional_overlay`, `modal_blocker`, or `non_visual`

Recommended table:

```markdown
## Display List

| Parent | Order | Name | Node Type | Asset Name | Resource | Position | Size | Size Source | Z Layer | Occlusion Policy | Binding |
|---|---:|---|---|---|---|---|---|---|---|---|---|
```

`layout_spec.json.objects[]` and `slots[]` should carry the same `zLayer` and `occlusionPolicy` values.

## Layer Order

The required rank is:

```text
background < content < foreground < overlay < modal < debug
```

Rows in one parent component must not move backwards in this rank as XML order increases.

Examples:

```text
0 background_scene  background  opaque_background
1 hero_card         content     normal
2 action_button     content     normal
3 screen_frame      foreground  transparent_frame
4 tutorial_mask     overlay     intentional_overlay
5 confirm_modal     modal       modal_blocker
```

## Opaque Background Rules

Nodes or resources whose names clearly contain `bg`, `background`, or `backdrop` are treated as background evidence even when the plan labels them incorrectly; they cannot bypass the rule by using `normal`.

An `opaque_background`:

- must use `Z Layer=background`
- must be the earliest visible direct child in its parent
- must not appear after content, foreground, overlay, or modal rows
- may cover the full component only because it is backmost

A full-screen background component placed after buttons, cards, lists, or status bars is a hard error even when its name contains `background`.

## Transparent Frame Rules

A full-size frame may appear after content only when:

- `Occlusion Policy=transparent_frame`
- the backing asset is declared transparent in `asset_manifest.json`, or the child component resolves to transparent frame assets
- the center area is intentionally transparent
- the visual review confirms it does not block intended interaction

Do not classify an opaque panel or full-screen screenshot as `transparent_frame` merely to bypass ordering checks.

## Overlay Rules

`intentional_overlay` and `modal_blocker` must be explicit. Record:

- what they cover
- whether they receive touch input
- the Controller/state that displays them
- the requirement ID that justifies the occlusion

A large overlay with no state/requirement trace is a blocker.

## XML Validation

During XML validation:

1. Map each numeric Display List row to one direct child of the owning component XML.
2. Require names to appear in the same relative order.
3. Require every `opaque_background` to precede normal content.
4. Reject duplicate `Order` values within one parent.
5. Reject layer-rank reversals.
6. Reject a missing or unclassified full-size background/frame row.

Error examples:

```text
display_list_z_layer_order_invalid
display_list_order_duplicate
opaque_background_not_backmost
xml_display_list_order_mismatch
xml_display_list_node_missing
```

## Manual Review

After FairyGUI Editor opens the package, verify:

- background is behind every content object
- transparent frame appears above content without covering the center
- no large component blocks buttons, lists, cards, or drag targets
- modal blockers appear only in their intended state
- visible order matches the approved design
