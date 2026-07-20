# FairyGUI UI Pipeline Skill 使用方法

## 位置

```text
D:\ChatGPTShare\skills\fairygui-ui-pipeline
```

## 适合做什么

用它把游戏 UI 从“需求想法”推进到 FairyGUI 可接入的生产资料：

1. 检查需求信息是否足够。
2. 生成 `ui_spec.md` 和 `visual_design_brief.md`。
3. 根据需求文档、UI 设计文档和参考图生成整屏设计稿。
4. 停止流水线，等待用户明确确认具体设计稿。
5. 设计稿确认通过后，进行语义分析、布局分析和资源规划。
6. 规划资源、sheet、manifest，并生成正式资源。
7. 按 manifest 切图并检查。
8. 生成 FairyGUI 包结构、组件层级、Controller、Transition、Relation、Gear 和 Unity 绑定字段。
9. 在 XML 严格模式下判断是否允许生成 `package.xml` 和组件 XML 草稿。
10. 输出校验报告和 FairyGUI 编辑器导入检查清单。

## 重要原则

当任务包含生成、重绘、换风格、还原或批量生产游戏 UI 图片资源时，开始前必须至少提供一张真实参考图，并明确它用于风格、布局、颜色、资产形状还是完整还原。没有参考图时，只能生成需求文档和资源清单草案，不能进入 imagegen。

当任务是根据需求或设计文档创建完整游戏界面时，必须先生成整屏设计稿。生成后必须停止，等待用户明确确认具体图片。AI 不得自行确认，也不能把“继续”“差不多”或沉默推断为批准。确认记录会绑定设计图 SHA-256，图片发生任何修改都必须重新确认。

每个图片资源必须分别声明：

- `sourcePixelSize`：实际 PNG 像素尺寸
- `displaySize`：FairyGUI 设计分辨率下的显示尺寸
- `scalePolicy`：是否允许缩放，以及缩放方式
- `renderMode`：normal、nine_slice、tile、fit、fill 等

XML 不是默认产物。只有满足下面条件时才允许生成 XML：

- 已完整读取 Skill 内置的 `references/fairygui-ai-generation-workflow.md`
- 已完整读取 Skill 内置的 `references/fairygui-xml-parsing-specification.md`
- 已运行 `scripts/verify_embedded_docs.py` 并确认两份完整文档未缺失、未截断
- 已读取 `references/fairygui-xml-contract.md`
- 已读取 `references/xml-strict-generation.md`
- 已有 `asset_manifest.json`
- 已有 `fgui_id_registry.json`
- 已有 `fgui_spec.md` 或明确的组件/displayList 计划
- 所有图片、组件、声音、字体资源都有稳定资源 ID
- 所有 `src` / `url` / `defaultItem` 都能对应到已注册资源 ID
- 实际图片像素与 `sourcePixelSize` 一致
- FairyGUI `<image size>`、Manifest `displaySize` 与布局文档尺寸一致
- 视觉资源由本 Skill 生成时，Manifest 中存在有效主参考图

整屏设计稿生成后，进入任何后续阶段前必须运行设计确认门禁，例如：

```bash
python scripts/check_design_approval.py \
  --root /path/to/UIProduction \
  --stage semantic_analysis \
  --out /path/to/UIProduction/reports/design_gate_report.json \
  --report-md /path/to/UIProduction/reports/design_gate_blocking_report.md
```

生成 XML 前还必须运行可执行门禁：

```bash
python scripts/check_xml_readiness.py \
  --root /path/to/UIProduction \
  --profile fresh \
  --require-design-approval \
  --resource-generation \
  --design-driven \
  --out /path/to/UIProduction/reports/xml_readiness_report.json \
  --report-md /path/to/UIProduction/reports/xml_blocking_report.md \
  --snapshot-out /path/to/UIProduction/reports/xml_generation_input_snapshot.json
```

使用了设计图、截图或参考 Mockup 时保留 `--design-driven`；本次项目由 Skill 生成或重绘视觉资源时保留 `--resource-generation`。只有纯 XML/绑定/校验任务才省略 `--resource-generation`。

缺少这些条件时，只能输出：

- XML生成阻塞报告
- manifest 修正建议
- fgui_id_registry 草案
- FairyGUI 拼装计划

不能输出带有 `包ID`、`资源ID`、`xxxx`、`背景资源ID` 等占位符的 XML。

## 推荐调用方式

### 从需求生成完整界面设计稿

```text
使用 fairygui-ui-pipeline skill，根据下面的游戏界面需求、UI 设计文档和已附带参考图：

1. 判断需求是否足够。
2. 生成 ui_spec.md 和 visual_design_brief.md。
3. 生成 1～2 张完整界面设计稿。
4. 创建 pending 状态的 design_approval.json。
5. 生成后立即停止，不要继续生成语义分析、layout_spec、asset_manifest、切图、FairyGUI 拼装或 XML，等待我确认具体设计图。

参考图用途：style_and_layout
需求：
……
```

### 确认设计稿后继续

用户确认前先保持 pending：

```bash
python scripts/record_design_approval.py \
  --root /path/to/UIProduction \
  --action pending \
  --file generated/design/screen_design_draft_v1.png \
  --note "等待用户确认"
```

用户明确确认具体文件后，再记录批准：

```bash
python scripts/record_design_approval.py \
  --root /path/to/UIProduction \
  --action approve \
  --file generated/design/screen_design_final.png \
  --approved-for semantic_analysis layout_analysis asset_planning resource_generation fairygui_assembly xml_generation \
  --confirmation-type user_confirmation \
  --recorded-by user \
  --note "用户明确确认此文件为最终整屏设计稿"
```

随后运行 `check_design_approval.py`，门禁通过后才能生成 `uxui_semantic_spec.md`、`component_state_map.json` 和 `layout_spec.json`。

### 从已有 UI 文档生成资源规划

```text
使用 fairygui-ui-pipeline skill，读取我的 ui_spec.md 和参考图，先登记 referenceImages，再生成 asset_manifest.json、sheet_plan.md 和 imagegen 提示词。资源必须声明 sourcePixelSize、displaySize、scalePolicy 和 renderMode。不要生成 XML。
```

### 检查切图

```text
使用 fairygui-ui-pipeline skill，检查 generated/sliced 里的 PNG 是否和 asset_manifest.json 对得上，然后生成 cut_report.json。
```

### 生成 FairyGUI 拼装计划，不生成 XML

```text
使用 fairygui-ui-pipeline skill，根据 ui_spec.md、asset_manifest.json 和切图目录，生成 fgui_spec.md、FairyGUI 包结构、组件层级、Controller、Transition、Relation、Gear 和 Unity 绑定字段。不要生成 XML。
```

### 进入 XML 严格模式

新生成 XML 使用 `fresh`；FairyGUI 编辑器已经接受、清理或导出的 XML 使用 `editor-compatible`。不能为了绕过新生成 XML 的错误而使用兼容模式。

```text
使用 fairygui-ui-pipeline skill，并进入 XML 严格模式 fresh。

必须完整读取：
- references/fairygui-ai-generation-workflow.md
- references/fairygui-xml-parsing-specification.md
- references/fairygui-xml-contract.md
- references/xml-strict-generation.md

请读取：
- ui_spec.md
- asset_manifest.json
- fgui_id_registry.json
- fgui_spec.md

如果缺少 asset_manifest.json、fgui_id_registry.json、资源注册信息或 XML 解析规则，不要生成 XML，只输出 XML生成阻塞报告。

禁止输出任何包含 包ID、资源ID、xxxx、背景资源ID、按钮资源ID 之类占位符的 XML。
```

## 标准产物目录

```text
UIProduction/
├── references/
│   └── ui_reference.png
├── specs/
│   ├── ui_spec.md
│   ├── visual_design_brief.md
│   └── fgui_spec.md
├── manifests/
│   ├── asset_manifest.json
│   └── fgui_id_registry.json
├── generated/
│   ├── design/
│   │   ├── screen_design_draft_v1.png
│   │   └── screen_design_final.png
│   ├── sheets/
│   ├── sliced/
│   └── preview/
├── fgui_xml/
│   └── cooking/
│       ├── package.xml
│       └── cooking_view.xml
└── reports/
    ├── design_draft_review.md
    ├── design_approval.json
    ├── design_gate_report.json
    ├── design_gate_blocking_report.md
    ├── cut_report.json
    ├── xml_readiness_report.json
    ├── xml_blocking_report.md
    ├── xml_generation_input_snapshot.json
    ├── pipeline_validate_report.json
    ├── xml_validate_report.json
    ├── xml_editor_compatible_report.json
    └── fgui_import_checklist.md
```

## 迁移到其他电脑

只需复制整个 `fairygui-ui-pipeline` 文件夹。完整原文已经内置在：

```text
references/fairygui-ai-generation-workflow.md
references/fairygui-xml-parsing-specification.md
```

不再依赖 `D:\ChatGPTShare\AI文档` 或其他外部路径。复制后先运行：

```bash
python scripts/verify_embedded_docs.py
```

该脚本会验证两份文档的存在性、精确字节数、标题、最后章节和版本记录。失败时不得继续流水线或 XML 工作。

## 校验脚本

内置完整文档校验：

```bash
python scripts/verify_embedded_docs.py
```

设计稿确认门禁：

```bash
python scripts/check_design_approval.py \
  --root /path/to/UIProduction \
  --stage semantic_analysis
```

基础流水线校验：

```bash
python scripts/validate_pipeline.py --root /path/to/UIProduction
```

新生成 XML 后运行：

```bash
python scripts/validate_fgui_xml.py \
  --xml-dir /path/to/UIProduction/fgui_xml/cooking \
  --manifest /path/to/UIProduction/manifests/asset_manifest.json \
  --registry /path/to/UIProduction/manifests/fgui_id_registry.json \
  --mode fresh \
  --out /path/to/UIProduction/reports/xml_validate_report.json
```

XML 被 FairyGUI 编辑器接受、清理或导出后，再运行：

```bash
python scripts/validate_fgui_xml.py \
  --xml-dir /path/to/UIProduction/fgui_xml/cooking \
  --manifest /path/to/UIProduction/manifests/asset_manifest.json \
  --registry /path/to/UIProduction/manifests/fgui_id_registry.json \
  --mode editor-compatible \
  --out /path/to/UIProduction/reports/xml_editor_compatible_report.json
```

运行 Skill 自带回归测试：

```bash
python scripts/verify_embedded_docs.py
python -m unittest discover -s tests -p "test_*.py"
```

Windows 也可以直接运行：

```bat
run_tests.cmd
```

## 正式使用原则

- 完整界面任务必须先生成整屏设计稿，并经过用户明确确认后才能进入下一阶段。
- AI 不能自行将 `design_approval.json` 写为 `approved`；批准必须来自用户或人工审核记录，并绑定具体文件 SHA-256。
- `record_design_approval.py --action approve` 只能在用户明确确认具体图片之后运行。
- `asset_manifest.json` 是参考图、资源、sheet、切图、像素尺寸、显示尺寸、缩放策略和 FairyGUI 映射的唯一真源。
- 视觉资源生产必须先通过 `references/visual-reference-contract.md`。
- 所有图片尺寸必须通过 `references/asset-size-contract.md`；旧字段 `size` 不能替代 `sourcePixelSize` 和 `displaySize`。
- `fgui_id_registry.json` 负责稳定 ID，重跑时不能全部随机。
- `references/fairygui-ai-generation-workflow.md` 和 `references/fairygui-xml-parsing-specification.md` 是随 Skill 一起迁移的完整原文，不允许只按摘要、桥接文件或外部路径生成。
- `references/xml-strict-generation.md` 是 XML 生成前的章节覆盖清单，不允许跳过。
- imagegen 和 FairyGUI XML 都要经过人工检查点。
- XML 生成顺序必须是：注册并冻结 ID → `package.xml` → 叶子组件 → 组合组件 → 主界面。
- 每次生成前写入 `reports/xml_generation_input_snapshot.json`，防止生成期间 Manifest 或 Registry 被悄悄修改。
- XML 草稿必须经过 FairyGUI 编辑器打开、发布、Unity 加载测试后，才算最终可用。
