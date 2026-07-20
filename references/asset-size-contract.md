# Asset Size Contract

Use this contract for every bitmap resource that will be generated, sliced, registered, or placed in FairyGUI.

## Core Rule

Every FairyGUI image size must be traceable to the project documents. Unexplained size differences are errors.

Do not use a single ambiguous `size` field for both source pixels and display layout. Record the source pixel dimensions, intended FairyGUI display dimensions, and scaling policy separately.

## Asset Manifest Fields

Recommended asset shape:

```json
{
  "name": "machine_fryer",
  "file": "generated/sliced/machine_fryer.png",
  "type": "equipment",
  "sourcePixelSize": [512, 512],
  "displaySize": [256, 256],
  "scalePolicy": "explicit_scale",
  "transparent": true,
  "pivot": "bottom_center",
  "renderMode": "normal",
  "nineSliceGrid": null,
  "fgui": {
    "resourceType": "image",
    "nodeType": "image",
    "component": "cooking_view",
    "binding": "machineFryer"
  }
}
```

Required for bitmap assets:

- `sourcePixelSize`: actual output file pixel size `[width,height]`
- `displaySize`: size used in the FairyGUI design resolution `[width,height]`
- `scalePolicy`: one allowed policy
- `renderMode`: rendering behavior

The old `size` field is legacy-only. New production files must not rely on it. During migration, `size` may be interpreted as `displaySize` only when the migration assumption is explicitly recorded; it never proves the actual source pixel size.

## Scale Policies

Allowed `scalePolicy` values:

- `pixel_exact`: source pixels and FairyGUI display size must be identical.
- `explicit_scale`: source and display sizes may differ, but both must be declared and XML must use `displaySize`.
- `nine_slice`: source and display sizes may differ; `nineSliceGrid` is required and must fit inside `sourcePixelSize`.
- `tile`: the source texture is tiled to the declared `displaySize`.
- `fit`: preserve aspect ratio and fit inside the declared display box.
- `fill`: preserve aspect ratio and fill the declared display box, allowing crop.
- `relation_driven`: XML uses the declared design-time `displaySize`; FairyGUI relations may change runtime size.

No implicit scaling is allowed. If `sourcePixelSize != displaySize`, a non-`pixel_exact` policy must be declared.

## Render Modes

Allowed `renderMode` values:

- `normal`
- `nine_slice`
- `tile`
- `fit`
- `fill`
- `loader_fit`
- `loader_fill`
- `relation_driven`

The render mode must agree with the scale policy. For example, `scalePolicy=nine_slice` requires `renderMode=nine_slice`.

## Size Consistency Chain

For each image asset, validate this chain:

```text
real image pixel dimensions
= asset_manifest.sourcePixelSize

asset_manifest.displaySize
= layout_spec object bbox width/height
= fgui_spec display-list size
= generated component XML image@size
```

Allowed exceptions must be explicit:

- `relation_driven`: XML still uses the design-time `displaySize`; runtime differences come from documented relations.
- `fit` / `fill`: XML node size equals `displaySize`; image content fitting behavior differs.
- `nine_slice` / `tile`: source pixels may differ from display size, but XML node size still equals `displaySize`.

## PNG File Validation

For generated PNG assets:

- the PNG header dimensions must equal `sourcePixelSize`
- width and height must be positive integers
- transparent assets should contain an alpha-capable PNG color type; visual alpha quality still needs image review
- sheet cells and sliced outputs must not silently resize assets after the manifest is frozen

When the environment cannot inspect files, record that pixel validation was skipped and keep XML generation blocked in `fresh` mode unless the user explicitly accepts the risk.

## Nine-Slice Rules

For `scalePolicy=nine_slice`, require:

```json
"nineSliceGrid": [x, y, width, height]
```

Rules:

- all values are non-negative integers
- width and height are positive
- `x + width <= sourcePixelSize[0]`
- `y + height <= sourcePixelSize[1]`
- stretchable center and fixed borders must match the design intent
- XML/editor configuration must use the same grid

## Layout Mapping

Every non-decorative image object in `layout_spec.json` should include:

```json
{
  "name": "machine_fryer_left",
  "assetName": "machine_fryer",
  "bbox": [100, 300, 256, 256],
  "sizeSource": "asset_manifest.displaySize"
}
```

If the layout size differs from `displaySize`, the object must state an override reason and an allowed policy. Unrecorded per-instance scaling is forbidden.

## XML Gate

In `fresh` mode:

- every `<image>` must have an explicit `size`
- XML `size` must equal Manifest `displaySize`
- XML `fileName` must map to the same Manifest asset
- the actual PNG dimensions must equal `sourcePixelSize`
- `pixel_exact` requires source and display sizes to match
- missing or ambiguous size fields block XML readiness

In `editor-compatible` mode, an editor-exported image that omits an explicit size may be warned rather than rejected only when source and display sizes are equal and the editor behavior is verified. A declared size that conflicts with `displaySize` remains an error.

## Failure Example

```text
asset machine_fryer size mismatch:
actual PNG: 512x512
manifest sourcePixelSize: 512x512
manifest displaySize: 256x256
XML image@size: 280x256
scalePolicy: explicit_scale

Result: error. XML size must equal displaySize.
```
