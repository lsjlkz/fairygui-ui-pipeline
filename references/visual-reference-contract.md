# Visual Reference Contract

Use this contract whenever the pipeline will design, generate, redraw, restyle, reconstruct, or batch-produce visual game UI resources.

## Core Rule

Visual resource production requires at least one real reference image before image generation begins.

Do not invent a complete visual style from text alone when this skill is being used to produce game art assets. If no valid reference image is available, stop before image generation and output a `视觉参考图阻塞报告`. The pipeline may still produce requirement notes, a tentative `ui_spec.md`, a draft asset inventory, and questions for the missing visual source.

This is a conditional gate, not a universal gate. A reference image is not required for tasks that only validate XML, repair resource IDs, review an existing manifest, generate Unity bindings, or inspect controllers/gears without producing or redesigning visual assets.

## Manifest Declaration

Declare visual-production intent and reference images at the top level of `asset_manifest.json`:

```json
{
  "production": {
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
  ]
}
```

When `production.generateVisualAssets=true`, `production.requiresVisualReference` must also be `true`, and at least one valid `referenceImages` entry must exist.

## Reference Roles

Allowed `role` values:

- `style_only`: use palette, rendering style, material language, lighting, and line/shape treatment; do not copy layout.
- `layout_only`: use regions, hierarchy, spacing, and composition; do not copy visual style.
- `asset_shape`: use silhouette, proportions, viewing angle, and construction of a specific asset class.
- `color_palette`: use only color relationships and palette direction.
- `style_and_layout`: use both visual style and composition as guidance.
- `full_reconstruction`: reconstruct the supplied design as closely as project rights and requirements permit.

Every reference must state its role. Do not silently broaden a `style_only` reference into a layout source or a `layout_only` reference into an art-style source.

## Required Fields

Each reference image requires:

- `file`: project-relative image path
- `role`: one allowed role
- `resolution`: actual `[width,height]` in pixels
- `isPrimary`: boolean
- `allowedUses`: non-empty list selected from `style`, `composition`, `layout`, `asset_generation`, `color`, `shape`, `reconstruction`

Rules:

- At least one reference must have `isPrimary=true`.
- Only one reference should be primary unless the project explicitly records a multi-primary blending rule.
- The file must exist when the environment can check files.
- The declared resolution must equal the real image pixel dimensions.
- References used for layout must be connected to `layout_spec.json.sourceImages`.
- References used for asset generation must be recorded in the relevant sheet/imagegen prompt batch.
- A generated mockup may become a reference only after it is saved, named, and accepted as a project source.

## Requirement Gate

Before resource generation, confirm:

- a valid primary reference image exists
- its role and allowed uses are explicit
- the user requirement and reference do not conflict silently
- the reference resolution and target design resolution are known
- any deliberate style/layout deviations are written into `ui_spec.md`

If the gate fails, output:

```md
# 视觉参考图阻塞报告

## 阻塞原因
- 缺少可读取的主参考图

## 仍可安全生成
- ui_spec.md 草案
- 资源类别清单
- 参考图需求说明

## 需要补充
- 至少一张参考图
- 参考图用途：风格、布局、资产形状或完整还原
```

## Automation Boundary

AI may analyze the reference and propose semantic/style mappings. Deterministic checks must verify file existence, image dimensions, manifest declarations, and reference-to-layout links. Human review remains required for whether the generated resources actually match the intended art direction.
