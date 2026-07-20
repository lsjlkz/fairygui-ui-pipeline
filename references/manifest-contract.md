# Manifest Contract

## Role

`asset_manifest.json` is the source of truth for art assets, sheet layout, slicing, and FairyGUI mapping. `fgui_id_registry.json` is the source of truth for stable package, resource, and component-instance IDs.

## asset_manifest.json

Recommended top-level shape:

```json
{
  "version": "0.1.0",
  "screen": "cooking_view",
  "resolution": [1920, 1080],
  "orientation": "landscape",
  "style": "bright_cartoon_45deg_cooking",
  "production": {
    "generateFullScreenDesign": true,
    "requiresDesignApproval": true,
    "generateVisualAssets": true,
    "requiresVisualReference": true
  },
  "referenceImages": [
    {
      "file": "references/ui_reference.png",
      "role": "style_and_layout",
      "resolution": [1920, 1080],
      "isPrimary": true,
      "allowedUses": ["style", "composition", "layout", "asset_generation"]
    }
  ],
  "package": {
    "name": "cooking",
    "outputPath": "fgui_xml/cooking"
  },
  "sheets": [],
  "assets": []
}
```

## Sheet Object

```json
{
  "name": "sheet_food_5x4",
  "file": "generated/sheets/sheet_food_5x4.png",
  "rows": 4,
  "cols": 5,
  "cellSize": [256, 256],
  "padding": [0, 0, 0, 0],
  "items": ["food_patty_raw", "food_patty_cooked"]
}
```

Rules:

- `rows * cols` is the maximum item count.
- Sheet names and files use lowercase snake_case.
- Keep one logical asset per cell.
- Do not place backgrounds and isolated transparent objects in the same sheet.

## Asset Object

```json
{
  "name": "food_patty_raw",
  "file": "generated/sliced/food_patty_raw.png",
  "type": "ingredient",
  "sourcePixelSize": [256, 256],
  "displaySize": [256, 256],
  "scalePolicy": "pixel_exact",
  "renderMode": "normal",
  "nineSliceGrid": null,
  "transparent": true,
  "trim": true,
  "pivot": "center",
  "sheet": "sheet_food_5x4",
  "cell": [0, 0],
  "states": ["raw"],
  "fgui": {
    "package": "cooking",
    "resourceType": "image",
    "component": "cooking_view",
    "layer": "ingredient_layer",
    "nodeType": "image",
    "binding": "foodPattyRaw"
  }
}
```

Required fields:

- `name`
- `file`
- `type`
- `sourcePixelSize`
- `displaySize`
- `scalePolicy`
- `renderMode`
- `transparent`
- `pivot`
- `fgui.resourceType`

The legacy `size` field is not sufficient for new production files. Read `references/asset-size-contract.md` before creating or validating bitmap assets.

When `production.generateFullScreenDesign=true`, `production.requiresDesignApproval` must also be true. Read `references/design-mockup-approval-contract.md`, generate the complete-screen mockup, and obtain a passing approval record before creating this production manifest or entering downstream stages.

When `production.generateVisualAssets=true`, at least one valid primary entry in `referenceImages` is mandatory. Read `references/visual-reference-contract.md` before image generation.

Recommended pivot values:

- `center`
- `bottom_center`
- `top_left`
- `[0.5, 0.5]`

## State Matrix

Assets with states should explicitly list them:

```json
{
  "name": "machine_fryer",
  "states": ["idle", "cooking", "done", "burned"]
}
```

Create corresponding FairyGUI controller pages:

- controller: `c_state`
- pages: `idle,cooking,done,burned`

## fgui_id_registry.json

Recommended shape:

```json
{
  "version": "0.1.0",
  "packages": {
    "cooking": {
      "id": "qdf53qpk",
      "resources": {
        "food_patty_raw": "mdvn0",
        "cooking_view.xml": "u7u5e"
      },
      "instances": {
        "cooking_view/bg_main": "n0_3qpk",
        "cooking_view/btn_start": "n1_3qpk"
      },
      "retired": []
    }
  }
}
```

Rules:

- First run may generate package/resource IDs.
- Reruns must reuse existing IDs.
- Deleted IDs go into `retired`; do not reuse them casually.
- `src` in XML must use resource IDs from this registry.

## Naming Rules

Use lowercase snake_case for files and asset names:

- `bg_kitchen_main`
- `table_workbench`
- `food_patty_raw`
- `machine_fryer_idle`
- `machine_fryer_done`
- `btn_start_normal`
- `icon_coin`
- `bubble_order_empty`
- `customer_01_idle`

Avoid:

- Chinese asset file names
- pinyin mixed with English
- arbitrary capitalization
- `图层1`
- `button copy`
- `按钮副本`
