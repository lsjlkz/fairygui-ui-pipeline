# Typography Fidelity Contract

## Purpose

Text shown inside an image-model-generated mockup is visual guidance, not a reproducible font specification. Exact FairyGUI typography requires deterministic font metrics and the same style parameters in the production preview and XML.

This contract prevents:

- approving image-model lettering and later approximating it with an unrelated system font;
- preview scripts hardcoding one font while FairyGUI XML uses the default font;
- losing color, size, alignment, spacing, stroke, shadow, or auto-size behavior between preview and XML;
- claiming pixel fidelity without a real font source and explicit text metrics.

## Required Production Declaration

```json
{
  "production": {
    "generateFullScreenDesign": true,
    "requiresTypographyFidelity": true
  }
}
```

Complete-screen projects must create:

```text
specs/typography_spec.json
reports/typography_fidelity_report.json
reports/typography_fidelity_report.md
```

A screen that intentionally contains no text may set `containsText=false`. That declaration still requires human approval before assembly, but styles, instances, and a text renderer are not required.

## Core Rule

The final production preview and FairyGUI XML must consume one typography specification.

Image-model text may guide:

- approximate hierarchy;
- serif versus sans-serif direction;
- broad weight and contrast;
- warm/cool color relationship;
- decorative versus utilitarian tone.

It cannot establish exact:

- font family/file;
- font size;
- glyph metrics;
- kerning or letter spacing;
- baseline and line height;
- stroke/shadow rendering;
- text bounding box.

Therefore the final production preview must replace image-model text with deterministic text or use an actual FairyGUI editor capture.

## Fidelity Modes

- `exact`: real font/bitmap-font identity and complete FairyGUI text attributes are specified and reproduced.
- `approximate_reference`: typography only approximates the image-model mockup. It may be used before production review, but cannot be the final approved production preview or XML source.

## Production Preview Text Modes

Allowed exact modes:

- `deterministic_text_overlay`: a deterministic renderer loads `typography_spec.json` and draws text with the declared font/style data.
- `fairygui_capture`: the production preview is captured directly from FairyGUI using the declared XML typography.

A preview renderer must not select fonts, sizes, or colors from unrelated hardcoded constants. It must load the same `typography_spec.json` used for XML generation.

## Supported FairyGUI Text Attributes

The project specification may declare these exact XML attributes:

- `font`
- `fontSize`
- `color`
- `align`
- `vAlign`
- `leading`
- `letterSpacing`
- `autoSize`
- `singleLine`
- `bold`
- `italic`
- `underline`
- `strikethrough`
- `strokeColor`
- `strokeSize`
- `shadowColor`
- `shadowOffset`

Core required attributes for every production style:

```text
font
fontSize
color
align
vAlign
autoSize
singleLine
```

Do not rely on FairyGUI defaults when visual fidelity is being reviewed.

## Required Project File

```json
{
  "version": "0.1.0",
  "screen": "screen_name",
  "containsText": true,
  "fidelityMode": "exact",
  "productionPreview": {
    "file": "generated/preview/assembled_screen.png",
    "textRenderingMode": "deterministic_text_overlay",
    "rendererScript": "scripts/render_production_preview.py",
    "renderTrace": "reports/typography_render_trace.json",
    "usesTypographySpec": true
  },
  "styles": [
    {
      "styleId": "panel_title",
      "xmlAttributes": {
        "font": "ui://packageidfontid",
        "fontSize": "23",
        "color": "#493426",
        "align": "center",
        "vAlign": "middle",
        "letterSpacing": "1",
        "autoSize": "none",
        "singleLine": "true",
        "bold": "true",
        "strokeColor": "#f3dfb6",
        "strokeSize": "1"
      }
    }
  ],
  "instances": [
    {
      "componentFile": "strategy_panel.xml",
      "xmlNodeName": "title",
      "hostComponentFile": "",
      "hostInstanceName": "",
      "styleId": "panel_title",
      "previewText": "STRATEGY",
      "localizationKey": "ui_strategy",
      "bbox": [90, 12, 153, 42]
    }
  ],
  "reviewStatus": "approved",
  "review": {
    "type": "user_confirmation",
    "recordedBy": "user",
    "note": "User approved the deterministic production typography."
  },
  "blockingForXml": false
}
```

`bbox` is `[x,y,width,height]`. For a normal text node it is local to `componentFile` and must match XML `xy` plus `size`.

For a reused Button/Label whose parent instance overrides title text, size, or color, declare the concrete host instance:

```json
{
  "componentFile": "action_button.xml",
  "xmlNodeName": "title",
  "hostComponentFile": "main_screen.xml",
  "hostInstanceName": "restart",
  "styleId": "secondary_button_title",
  "previewText": "RESTART",
  "localizationKey": "ui_restart",
  "bbox": [306, 608, 211, 51]
}
```

In this form, `bbox` is local to `hostComponentFile`. The validator resolves the referenced component, reads the parent `<Button>` or `<Label>` override, maps `titleFontSize` to effective `fontSize` and `titleColor` to effective `color`, and calculates the effective text bounds from the base component size, host instance size, and width/height relations. `hostComponentFile` and `hostInstanceName` must be provided together.

## Deterministic Render Trace

A deterministic text-overlay renderer must write:

```text
reports/typography_render_trace.json
```

Recommended shape:

```json
{
  "typographySpecSha256": "<current-typography-spec-sha256>",
  "rendererScript": "scripts/render_production_preview.py",
  "previewFile": "generated/preview/assembled_screen.png",
  "instances": [
    {
      "componentFile": "strategy_panel.xml",
      "xmlNodeName": "title",
      "styleId": "panel_title",
      "previewText": "STRATEGY",
      "bbox": [90, 12, 153, 42],
      "xmlAttributes": {
        "font": "Georgia",
        "fontSize": "23",
        "color": "#493426",
        "align": "center",
        "vAlign": "middle",
        "autoSize": "none",
        "singleLine": "true",
        "bold": "true",
        "strokeColor": "#f3dfb6",
        "strokeSize": "1"
      }
    }
  ]
}
```

The validator compares the trace against the exact current `typography_spec.json` bytes and every declared text instance. Merely mentioning `typography_spec.json` in a renderer script is insufficient. Missing instances, extra instances, changed bbox values, changed text, changed style IDs, or changed resolved attributes are blocking.

The renderer should generate the trace during the same execution that writes the production preview. Do not hand-author or copy a stale trace from another render.

## Font Identity

For exact fidelity, `font` must resolve to a deterministic project font:

- a registered FairyGUI bitmap/dynamic font resource URL; or
- an explicitly standardized system font that is guaranteed on every target/editor machine and recorded by exact family name.

Project font resources are preferred. A preview script path such as `C:\Windows\Fonts\georgiab.ttf` is not sufficient unless the FairyGUI project uses the same font identity and the target platform guarantees it.

Never expose or distribute font files through this Skill. The project remains responsible for font licensing and installation.

## Preview And XML Consistency

For every text instance, XML must match the typography specification exactly:

- tag is `text` or `richtext`;
- `name` equals `xmlNodeName`;
- all declared style attributes match;
- `xy` and `size` equal `bbox` for a direct component text target;
- visible preview `text` equals `previewText`;
- localization identity is stored as `customData="loc:<localizationKey>"` when declared.

For instance-level Button/Label typography:

- `hostComponentFile` resolves to a real parent XML;
- exactly one `<component name="hostInstanceName">` references `componentFile`;
- the referenced component root uses `extention="Button"` or `extention="Label"`;
- the host instance contains the matching `<Button>` or `<Label>` parameter node;
- `titleFontSize` and `titleColor` determine effective `fontSize` and `color` when present;
- `title` determines effective preview text when present;
- the effective host-local bbox, after width/height relations, equals `bbox`;
- instance-specific localization uses host `customData="loc:<key>"`, unless the instance keeps the base title and base localization unchanged.

A preview renderer may not hardcode a smaller brown secondary-button label while XML only overrides title/icon and leaves the base 27px light title style.

## Human Approval

Final typography must be human-approved. AI/model self-approval is invalid.

The production-preview approval should occur only after:

- runtime bitmaps are frozen;
- deterministic text is applied;
- colors, sizes, spacing, stroke, and shadow have been reviewed at the actual design resolution.

## Blocking Conditions

- `typography_fidelity_not_required`
- `typography_spec_missing`
- `approximate_typography_cannot_be_final_preview`
- `production_preview_text_mode_invalid`
- `preview_renderer_does_not_load_typography_spec`
- `preview_renderer_hardcoded_font`
- `typography_core_attributes_missing`
- `typography_font_size_invalid`
- `typography_color_invalid`
- `typography_instance_target_missing`
- `typography_host_target_incomplete`
- `typography_host_component_xml_missing`
- `typography_host_component_xml_invalid`
- `typography_host_instance_unresolved`
- `typography_host_component_file_mismatch`
- `typography_host_extension_unsupported`
- `typography_host_extension_override_missing`
- `typography_style_unresolved`
- `typography_xml_node_unresolved`
- `typography_xml_attribute_mismatch`
- `typography_xml_bbox_mismatch`
- `typography_preview_text_mismatch`
- `typography_localization_mapping_missing`
- `typography_review_not_approved`
- `typography_ai_self_approval_forbidden`
- `typography_render_trace_missing`
- `typography_render_trace_file_missing`
- `typography_render_trace_spec_hash_mismatch`
- `typography_render_trace_renderer_mismatch`
- `typography_render_trace_preview_mismatch`
- `typography_render_trace_instance_missing`
- `typography_render_trace_host_target_incomplete`
- `typography_render_trace_instance_extra`
- `typography_render_trace_style_mismatch`
- `typography_render_trace_text_mismatch`
- `typography_render_trace_bbox_mismatch`
- `typography_render_trace_attributes_mismatch`

## Validation Command

```bash
python scripts/validate_typography_fidelity.py \
  --root UIProduction \
  --stage xml_generation \
  --xml-dir UIProduction/fgui_xml/<package_name> \
  --out UIProduction/reports/typography_fidelity_report.json \
  --report-md UIProduction/reports/typography_fidelity_report.md
```

A visual comparison against image-model text can guide art direction, but it cannot replace deterministic typography validation.
