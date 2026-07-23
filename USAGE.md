# FairyGUI UI Pipeline Skill 使用方法


## 适合做什么

用它把游戏 UI 从“需求想法”推进到 FairyGUI 可接入的生产资料：

1. 检查需求信息是否足够。
2. 生成 `ui_spec.md` 和 `visual_design_brief.md`。
3. 根据需求文档、UI 设计文档和参考图生成整屏设计稿。
4. 停止流水线，等待用户明确确认具体设计稿。
5. 设计稿确认通过后，结合需求文档、UI/UX 设计文档和确认设计稿进行语义、状态归属、Controller/Gear 与布局分析。
6. 规划资源、sheet、manifest，并生成正式资源。
7. 按 manifest 切图并检查。
8. 生成 FairyGUI 包结构、组件层级、Controller、Transition、Relation、Gear 和 Unity 绑定字段。
9. 在 XML 严格模式下判断是否允许生成 `package.xml` 和组件 XML 草稿。
10. 输出校验报告和 FairyGUI 编辑器导入检查清单。
11. 输出总耗时、主动处理耗时、人工等待耗时、外部工具耗时，以及每个阶段的耗时和返工次数。

## 阶段耗时记录

完整流程开始前必须初始化计时：

```bash
python scripts/record_pipeline_timing.py --root /path/to/UIProduction init
```

每个阶段开始和结束时分别记录：

```bash
python scripts/record_pipeline_timing.py \
  --root /path/to/UIProduction \
  start --stage requirement_intake

python scripts/record_pipeline_timing.py \
  --root /path/to/UIProduction \
  finish --stage requirement_intake \
  --status completed \
  --artifact specs/ui_spec.md
```

不适用阶段必须显式标记，不能直接从报告中消失：

```bash
python scripts/record_pipeline_timing.py \
  --root /path/to/UIProduction \
  skip --stage sheet_slicing \
  --note "本次没有使用 Sprite Sheet"
```

设计稿发给用户后，结束 `design_mockup_generation`，立即开始 `design_approval`。这段跨会话时间会单独计入“人工等待”，不会混入主动生产耗时。等待期间可写临时报告：

```bash
python scripts/record_pipeline_timing.py --root /path/to/UIProduction snapshot
```

流程结束后必须执行：

```bash
python scripts/record_pipeline_timing.py \
  --root /path/to/UIProduction \
  finalize --status completed

python scripts/record_pipeline_timing.py \
  --root /path/to/UIProduction \
  validate
```

最终生成：

```text
reports/pipeline_stage_timings.json
reports/pipeline_stage_timings.md
```

完整状态 `completed` 要求 16 个标准阶段全部为 `completed` 或 `skipped`。阻塞、失败或尚未完成的流程必须使用 `blocked`、`failed` 或 `partial`，不能伪装成完整流程。

返工时使用 `--rework` 新增一次尝试，旧尝试和耗时必须保留。

## 重要原则

当任务包含生成、重绘、换风格、还原或批量生产游戏 UI 图片资源时，开始前必须至少提供一张真实参考图，并明确它用于风格、布局、颜色、资产形状还是完整还原。没有参考图时，只能生成需求文档和资源清单草案，不能进入 imagegen。

当任务是根据需求或设计文档创建完整游戏界面时，必须先生成整屏设计稿。生成后必须停止，等待用户明确确认具体图片。AI 不得自行确认，也不能把“继续”“差不多”或沉默推断为批准。确认记录会绑定设计图 SHA-256，图片发生任何修改都必须重新确认。

每个图片资源必须分别声明：

- `sourcePixelSize`：实际 PNG 像素尺寸
- `displaySize`：FairyGUI 设计分辨率下的显示尺寸
- `scalePolicy`：是否允许缩放，以及缩放方式
- `renderMode`：normal、nine_slice、tile、fit、fill 等
- `packageRelativeFile`：相对于 `package.xml` 所在包目录的精确资源路径

XML 不是默认产物。只有满足下面条件时才允许生成 XML：

- 已完整读取 Skill 内置的 `references/fairygui-ai-generation-workflow.md`
- 已完整读取 Skill 内置的 `references/fairygui-xml-parsing-specification.md`
- 已运行 `scripts/verify_embedded_docs.py` 并确认两份完整文档未缺失、未截断
- 已读取 `references/fairygui-xml-contract.md`
- 已读取 `references/xml-strict-generation.md`
- 已读取 `references/semantic-controller-mapping-contract.md`
- 已读取 `references/component-reuse-parameterization-contract.md`
- 已读取 `references/component-instance-configuration-contract.md`
- 已读取 `references/display-list-z-order-contract.md`
- 已读取 `references/bitmap-icon-source-contract.md`
- 已读取 `references/visual-part-coverage-contract.md`
- 已读取 `references/package-resource-path-contract.md`
- `validate_semantic_controller_mapping.py --stage xml_generation` 已通过
- `validate_component_reuse.py --stage xml_generation` 已通过
- `validate_display_list_z_order.py --stage xml_generation` 已通过
- `validate_bitmap_asset_provenance.py --stage xml_generation` 已通过
- `validate_visual_part_coverage.py --stage xml_generation` 已通过
- 已有 `asset_manifest.json`
- 已有 `fgui_id_registry.json`
- 已有 `fgui_spec.md` 或明确的组件/displayList 计划
- 所有图片、组件、声音、字体资源都有稳定资源 ID
- 所有 `src` / `url` / `defaultItem` 都能对应到已注册资源 ID
- 实际图片像素与 `sourcePixelSize` 一致
- FairyGUI `<image size>`、Manifest `displaySize` 与布局文档尺寸一致
- 视觉资源由本 Skill 生成时，Manifest 中存在有效主参考图
- 每个文件资源满足 `asset.file == package.outputPath/packageRelativeFile`
- `package.xml path+name` 和组件 `fileName` 都能在包目录中精确找到文件
- 外部 `<Button .../>` / `<Label .../>` 覆盖节点与目标组件 `extention` 一致，且标题、图标、声音 URL 均可验证
- 每个复用组件都在 `component_state_map.components[].reusePlan` 和 `fgui_spec.md` Component Reuse Plan 中声明基组件、参数字段、子组件和允许的变体理由
- 需要由父组件固定 Controller 页时，目标 Controller 设置 `exported="true"`，实例声明 `controllerParameters`，父 XML 精确写入 `controller="名称,页索引"`
- Display List 已声明 `Z Layer` 与 `Occlusion Policy`；不透明背景位于 XML 最前部
- 每个小图标都有合法 `assetSource`，且不是 Graph/SVG/字体/PIL 几何生成
- 每个复用组件实例都在 `component_state_map.visualInstances` 和 `fgui_spec.md` Instance Configuration 中有明确配置
- `component_visual_parts.json` 已记录设计稿中所有必需可见部件，并在 Manifest 或 XML 中声明实现
- 语义不同的实例不能全部使用同一个未配置默认组件，也不能仅因标题、图标、立绘、数值、颜色、尺寸或默认页不同就拆成多份同构 XML
- 小图标、面板框、标题装饰、背景、分隔线和状态标记不能因为非交互或尺寸小而被静默省略
- 变体组件默认 Controller 页必须匹配实例声明，编辑器预览不能直接显示未解析的 `@ui_...` Key

整屏设计稿生成后，进入任何后续阶段前必须运行设计确认门禁。确认通过后，还必须校验需求状态、语义归属和 Controller/Gear 映射：

```bash
python scripts/check_design_approval.py \
  --root /path/to/UIProduction \
  --stage semantic_analysis \
  --out /path/to/UIProduction/reports/design_gate_report.json \
  --report-md /path/to/UIProduction/reports/design_gate_blocking_report.md

python scripts/validate_semantic_controller_mapping.py \
  --root /path/to/UIProduction \
  --stage semantic_analysis \
  --out /path/to/UIProduction/reports/semantic_controller_mapping_report.json \
  --report-md /path/to/UIProduction/reports/semantic_controller_mapping_report.md

python scripts/validate_component_reuse.py \
  --root /path/to/UIProduction \
  --stage semantic_analysis \
  --out /path/to/UIProduction/reports/component_reuse_report.json \
  --report-md /path/to/UIProduction/reports/component_reuse_report.md

python scripts/validate_bitmap_asset_provenance.py \
  --root /path/to/UIProduction \
  --stage asset_planning \
  --out /path/to/UIProduction/reports/bitmap_asset_provenance_report.json \
  --report-md /path/to/UIProduction/reports/bitmap_asset_provenance_report.md

python scripts/validate_visual_part_coverage.py \
  --root /path/to/UIProduction \
  --stage asset_planning \
  --out /path/to/UIProduction/reports/visual_part_coverage_report.json \
  --report-md /path/to/UIProduction/reports/visual_part_coverage_report.md
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

使用了设计图、截图或参考 Mockup 时保留 `--design-driven`；本次项目由 Skill 生成或重绘视觉资源时保留 `--resource-generation`。当 Manifest 声明 `generateFullScreenDesign=true` 或 `requiresDesignApproval=true` 时，XML 门禁会自动启用设计驱动与语义 Controller/Gear 校验，即使遗漏 `--design-driven` 也不能绕过。只有纯 XML/绑定/校验任务才省略 `--resource-generation`。

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
使用 fairygui-ui-pipeline skill，根据 ui_spec.md、component_state_map.json、component_visual_parts.json、asset_manifest.json 和切图目录，生成 fgui_spec.md、FairyGUI 包结构、组件层级、Component Reuse Plan、Controller、Gear、Instance Configuration、Visual Part Coverage、Transition、Relation 和 Unity 绑定字段。Display List 必须包含 Z Layer 与 Occlusion Policy，并按背景→内容→前景/遮罩排序。每个复用组件必须声明 reusePlan、基组件、可参数化字段和可复用子组件；每个复用实例必须声明 xmlInstanceName、componentFile、configurationMode、Controller Pages、Controller Parameters、Preview Values 和 Runtime Bindings。可导出的 Controller 优先通过父实例 controller="名称,页索引" 传入。标题、图标、立绘、数值、颜色、尺寸或默认页差异不能单独构成 variant_component。每个小图标必须来自审核位图并声明 assetSource，禁止 Graph/SVG/字体/PIL 几何替代。不要生成 XML。
```

### 暂存完整 FairyGUI 包资源

在生成 XML 前，先把所有资源放进最终包目录：

```text
UIProduction/fgui_xml/cooking/
├── package.xml
├── cooking_view.xml
└── art/
    └── bg_main.png
```

Manifest 必须区分：

```json
{
  "package": {
    "outputPath": "fgui_xml/cooking"
  },
  "assets": [
    {
      "file": "fgui_xml/cooking/art/bg_main.png",
      "packageRelativeFile": "art/bg_main.png"
    }
  ]
}
```

`file` 相对于 UIProduction；`packageRelativeFile` 相对于 `package.xml`。`package.xml` 和组件 XML 只能使用后者，不能写入 `fgui_xml/cooking/` 前缀。

### 进入 XML 严格模式

新生成 XML 使用 `fresh`；FairyGUI 编辑器已经接受、清理或导出的 XML 使用 `editor-compatible`。不能为了绕过新生成 XML 的错误而使用兼容模式。

```text
使用 fairygui-ui-pipeline skill，并进入 XML 严格模式 fresh。

必须完整读取：
- references/fairygui-ai-generation-workflow.md
- references/fairygui-xml-parsing-specification.md
- references/fairygui-xml-contract.md
- references/semantic-controller-mapping-contract.md
- references/component-reuse-parameterization-contract.md
- references/component-instance-configuration-contract.md
- references/display-list-z-order-contract.md
- references/bitmap-icon-source-contract.md
- references/visual-part-coverage-contract.md
- references/package-resource-path-contract.md
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
│   ├── component_visual_parts.json
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
│       ├── cooking_view.xml
│       └── art/
│           └── bg_main.png
└── reports/
    ├── design_draft_review.md
    ├── design_approval.json
    ├── design_gate_report.json
    ├── design_gate_blocking_report.md
    ├── semantic_controller_mapping_report.json
    ├── semantic_controller_mapping_report.md
    ├── component_reuse_report.json
    ├── component_reuse_report.md
    ├── display_list_z_order_report.json
    ├── display_list_z_order_report.md
    ├── bitmap_asset_provenance_report.json
    ├── bitmap_asset_provenance_report.md
    ├── visual_part_coverage_report.json
    ├── visual_part_coverage_report.md
    ├── pipeline_stage_timings.json
    ├── pipeline_stage_timings.md
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

语义状态、Controller 和 Gear 映射校验：

```bash
python scripts/validate_semantic_controller_mapping.py \
  --root /path/to/UIProduction \
  --stage xml_generation
```

已有 XML 时追加：

```bash
--xml-dir /path/to/UIProduction/fgui_xml/cooking
```

Display List 层级校验：

```bash
python scripts/validate_display_list_z_order.py \
  --root /path/to/UIProduction \
  --stage xml_generation \
  --xml-dir /path/to/UIProduction/fgui_xml/cooking \
  --out /path/to/UIProduction/reports/display_list_z_order_report.json \
  --report-md /path/to/UIProduction/reports/display_list_z_order_report.md
```

阶段耗时记录与校验：

```bash
python scripts/record_pipeline_timing.py --root /path/to/UIProduction init
python scripts/record_pipeline_timing.py --root /path/to/UIProduction start --stage requirement_intake
python scripts/record_pipeline_timing.py --root /path/to/UIProduction finish --stage requirement_intake --status completed
python scripts/record_pipeline_timing.py --root /path/to/UIProduction finalize --status completed
python scripts/record_pipeline_timing.py --root /path/to/UIProduction validate
```

命令型阶段可以自动包裹计时：

```bash
python scripts/record_pipeline_timing.py \
  --root /path/to/UIProduction \
  run --stage validation -- \
  python scripts/validate_pipeline.py --root /path/to/UIProduction
```

图标位图来源校验：

```bash
python scripts/validate_bitmap_asset_provenance.py \
  --root /path/to/UIProduction \
  --stage xml_generation \
  --out /path/to/UIProduction/reports/bitmap_asset_provenance_report.json \
  --report-md /path/to/UIProduction/reports/bitmap_asset_provenance_report.md
```

组件复用与参数化校验：

```bash
python scripts/validate_component_reuse.py \
  --root /path/to/UIProduction \
  --stage xml_generation \
  --xml-dir /path/to/UIProduction/fgui_xml/cooking \
  --out /path/to/UIProduction/reports/component_reuse_report.json \
  --report-md /path/to/UIProduction/reports/component_reuse_report.md
```

视觉部件覆盖校验：

```bash
python scripts/validate_visual_part_coverage.py \
  --root /path/to/UIProduction \
  --stage xml_generation \
  --xml-dir /path/to/UIProduction/fgui_xml/cooking \
  --out /path/to/UIProduction/reports/visual_part_coverage_report.json \
  --report-md /path/to/UIProduction/reports/visual_part_coverage_report.md
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

`validate_fgui_xml.py` 检测到 `component_state_map.json` 或完整界面设计声明时，会自动交叉检查需求状态、Controller 页面、Gear 目标、Instance Configuration 和实际组件 XML。它还会把 `package.xml path+name` 和组件 `fileName` 按包目录精确解析；仅文件名相同但路径错误也会失败。对于外部 `<Button .../>` / `<Label .../>` 参数节点，它会校验目标组件扩展类型、允许字段和 `ui://` 引用。对于复用实例，它会校验父 XML 实例、变体组件默认页、外部参数和可读预览文本。

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
- 所有包内文件路径必须通过 `references/package-resource-path-contract.md`；不能把 UIProduction 根目录路径直接写进 FairyGUI XML。
- FairyGUI 包目录必须作为完整原子包复制，不能分别维护一份 XML 复制清单和图片复制清单。
- `fgui_id_registry.json` 负责稳定 ID，重跑时不能全部随机。
- `references/fairygui-ai-generation-workflow.md` 和 `references/fairygui-xml-parsing-specification.md` 是随 Skill 一起迁移的完整原文，不允许只按摘要、桥接文件或外部路径生成。
- `references/semantic-controller-mapping-contract.md` 负责把需求状态、设计语义、状态归属、Controller 页面、Gear 目标、外部 Button/Label 实例参数和 XML 实现串成同一条可校验链路。
- `references/component-reuse-parameterization-contract.md` 负责优先合并同构组件、声明基组件与参数字段、抽取可复用子组件，并阻止内容差异被错误拆成 XML 变体。
- `references/display-list-z-order-contract.md` 负责约束 FairyGUI XML 从后到前的绘制顺序，防止背景或大组件放在后部覆盖内容。
- `references/bitmap-icon-source-contract.md` 负责禁止矢量/程序化图标替代，要求小图标来自审核位图并保留来源证据。
- `references/component-instance-configuration-contract.md` 负责防止不同语义的复用实例全部落到同一个默认页面，并约束外部覆盖、Controller 页面、运行时绑定、结构性变体和可读预览文本。
- `references/visual-part-coverage-contract.md` 负责把确认设计稿里的每个必需可见部件映射到 Manifest 和 XML；角色名、部件角色和项目业务名称全部来自项目文件，不在 Skill 中写死。
- `references/pipeline-stage-timing-contract.md` 负责标准阶段编号、主动/等待/外部时间分类、返工尝试保留和最终耗时报告；流程开始前必须初始化，结束后必须 finalize 与 validate。
- `references/xml-strict-generation.md` 是 XML 生成前的章节覆盖清单，不允许跳过。
- imagegen 和 FairyGUI XML 都要经过人工检查点。
- XML 生成顺序必须是：注册并冻结 ID → 暂存完整包资源 → 校验包内路径 → `package.xml` → 可参数化叶子/子组件 → 基础复合组件 → 经结构校验允许的变体 → 主界面。
- 每次生成前写入 `reports/xml_generation_input_snapshot.json`，防止生成期间 Manifest 或 Registry 被悄悄修改。
- XML 草稿必须经过 FairyGUI 编辑器打开、按设计分辨率截图并与确认设计稿对照、发布、Unity 加载测试后，才算最终可用。
- 视觉对照必须确认没有重复默认头像/图标、空白按钮、白色占位块、原始本地化 Key 或漏掉的实例状态。
- 最终交付必须输出每个标准阶段的状态、尝试次数和耗时，并分别汇总总墙钟时间、主动处理时间、人工等待时间、外部工具时间和未跟踪时间。
