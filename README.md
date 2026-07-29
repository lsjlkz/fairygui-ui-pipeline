

# FairyGUI UI Pipeline

半自动化游戏 UI 生产流水线 | Semi-automated Game UI Production Pipeline

## 概述

FairyGUI UI Pipeline 是一套完整的游戏 UI 生产解决方案，旨在将 UI 需求、设计稿、图像资源转换为符合 FairyGUI 规范的可用资源包。该流水线采用**半自动化**设计，结合人工审核与自动化验证，确保 UI 生产质量与效率的平衡。

## 核心功能

### 📋 全流程管理
- **需求 Intake**：结构化需求采集与确认
- **UX/UI 规范**：语义化的 UI 规格说明
- **视觉设计简报**：设计目标与约束明确定义
- **全屏设计稿生成**：AI 辅助设计稿生成
- **人工审核批准**：强制性的设计审核流程
- **语义分析**：需求到设计的语义映射
- **布局分析**：设计到布局的转换
- **资源规划**：图片资源与纹理集规划
- **图像生成**：生产级图像资源生成
- **纹理集切片**：优化的切片方案
- **FairyGUI 拼装规划**：组件化拼装策略
- **资源暂存**：包资源阶段化管理
- **XML 草稿生成**：符合规范的 XML 输出
- **多维验证**：多层次质量验证
- **编辑器发布**：Unity 集成准备
- **冒烟测试**：运行时验证
- **时序定稿**：最终交付确认

### 🔒 严格模式
- **XML 严格模式**：强制性的 XML 规范检查
- **设计审批门**：全屏设计稿必须经过人工审批
- **语义映射门**：状态与控制器的语义对应必须明确
- **资产隔离**：视觉资产与逻辑资产的严格分离

### ✅ 自动化验证
- **资源溯源验证**：确保资源来源清晰可查
- **组件复用验证**：检测重复与复用机会
- **语义控制器映射**：控制器与 UI 状态的对应验证
- **视觉部分覆盖**：UI 组件的视觉元素完整性
- **显示列表 Z序**：层级结构的正确性验证
- **字体保真度**：文本渲染的一致性验证
- **资产隔离合规**：隔离规范的遵循检测
- **生产预览血缘**：资源衍生的追踪验证

## 目录结构

```
fairygui-ui-pipeline/
├── SKILL.md                    # 技能描述文档
├── USAGE.md                    # 使用指南（中文）
├── agents/                     # Agent 配置
│   └── openai.yaml
├── references/                 # 规范与契约文档
│   ├── pipeline.md             # 流水线定义
│   ├── fairygui-xml-parsing-specification.md  # XML 解析规范
│   ├── fairygui-ai-generation-workflow.md     # AI 自动生成流程
│   ├── manifest-contract.md    # Manifest 契约
│   ├── design-mockup-approval-contract.md     # 设计审批契约
│   ├── design-to-layout-contract.md           # 设计转布局契约
│   ├── component-reuse-parameterization-contract.md  # 组件复用契约
│   ├── visual-part-coverage-contract.md       # 视觉部分覆盖契约
│   ├── semantic-controller-mapping-contract.md # 语义控制器映射契约
│   ├── display-list-z-order-contract.md       # 显示列表 Z序契约
│   ├── typography-fidelity-contract.md        # 字体保真度契约
│   ├── asset-isolation-contract.md            # 资产隔离契约
│   ├── production-preview-lineage-contract.md  # 生产预览血缘契约
│   ├── visual-reference-contract.md           # 视觉参考契约
│   ├── component-instance-configuration-contract.md  # 组件实例配置契约
│   ├── asset-size-contract.md                 # 资源尺寸契约
│   ├── bitmap-icon-source-contract.md         # 位图标来源契约
│   ├── package-resource-path-contract.md      # 包资源路径契约
│   ├── pipeline-stage-timing-contract.md      # 流水线时序契约
│   ├── xml-strict-generation.md               # XML 严格生成
│   ├── output-templates.md                    # 输出模板
│   └── embedded-docs-manifest.json            # 嵌入文档清单
├── scripts/                   # 验证与工具脚本
│   ├── check_design_approval.py        # 设计审批检查
│   ├── check_xml_readiness.py          # XML 就绪检查
│   ├── image_metadata.py               # 图像元数据读取
│   ├── record_design_approval.py       # 记录设计审批
│   ├── record_pipeline_timing.py       # 记录流水线时序
│   ├── record_production_preview_approval.py  # 记录生产预览审批
│   ├── validate_asset_isolation.py     # 验证资产隔离
│   ├── validate_bitmap_asset_provenance.py    # 验证资源溯源
│   ├── validate_component_reuse.py     # 验证组件复用
│   ├── validate_display_list_z_order.py      # 验证 Z序
│   ├── validate_fgui_xml.py            # 验证 FairyGUI XML
│   ├── validate_pipeline.py            # 验证流水线
│   ├── validate_production_preview_lineage.py # 验证血缘
│   ├── validate_semantic_controller_mapping.py # 验证语义映射
│   ├── validate_typography_fidelity.py # 验证字体保真
│   ├── validate_visual_part_coverage.py      # 验证视觉覆盖
│   └── verify_embedded_docs.py         # 验证嵌入文档
└── tests/                       # 单元测试
    ├── test_asset_isolation.py
    ├── test_asset_isolation_integration.py
    ├── test_pipeline_timing.py
    ├── test_preview_typography_integration.py
    ├── test_production_preview_approval.py
    ├── test_production_preview_lineage.py
    ├── test_registry_instance_scope.py
    ├── test_strict_validators.py
    ├── test_typography_fidelity.py
    └── test_typography_instance_override.py
```

## 快速开始

### 前置条件

- Python 3.8+
- FairyGUI Editor（用于发布和测试）
- Unity 2020+（用于集成测试）

### 安装

1. 克隆仓库：
```bash
git clone <repository-url>
cd fairygui-ui-pipeline
```

2. 安装依赖（如有需要）：
```bash
pip install -r requirements.txt
```

### 基本使用流程

#### 1. 创建项目结构
按照 `references/output-templates.md` 中的模板创建必要的规范文档。

#### 2. 运行设计审批
```bash
python scripts/record_design_approval.py --root /path/to/project --approve design.png
```

#### 3. 验证资产隔离
```bash
python scripts/validate_asset_isolation.py --root /path/to/project --stage asset_planning
```

#### 4. 生成 XML 严格模式
```bash
python scripts/check_xml_readiness.py --root /path/to/project --profile fresh
```

#### 5. 验证最终输出
```bash
python scripts/validate_fgui_xml.py --root /path/to/project --mode fresh
```

## 流水线阶段详解

| 阶段 | ID | 说明 |
|------|-----|------|
| 需求 Intake | `requirement_intake` | 采集并确认 UI 需求 |
| UX/UI 规格 | `uxui_spec` | 定义语义化的 UI 规格 |
| 视觉设计简报 | `visual_design_brief` | 明确设计目标与约束 |
| 全屏设计生成 | `full_screen_design` | AI 辅助生成设计稿 |
| 设计审批 | `design_approval` | 人工审批设计稿 |
| 语义分析 | `semantic_analysis` | 需求与设计的语义映射 |
| 布局分析 | `layout_analysis` | 设计到布局的转换 |
| 资源规划 | `asset_planning` | 图片资源规划 |
| 图像生成 | `image_generation` | 生产级图像生成 |
| 纹理集切片 | `sheet_slice` | 优化切片方案 |
| 拼装规划 | `fgui_assembly` | 组件化拼装策略 |
| 资源暂存 | `resource_stage` | 包资源阶段管理 |
| XML 生成 | `xml_generation` | XML 草稿生成 |
| 质量验证 | `validation` | 多维度质量验证 |
| 编辑器发布 | `editor_publish` | Unity 集成准备 |
| 冒烟测试 | `smoke_test` | 运行时验证 |
| 最终交付 | `final_handoff` | 最终交付确认 |

## 输出产物

流水线各阶段会产生以下产物：

- `ui_spec.md` - UI 规格文档
- `visual_design_brief.md` - 视觉设计简报
- `design_approval.json` - 设计审批记录
- `uxui_semantic_spec.md` - 语义规格文档
- `layout_spec.json` - 布局规格
- `asset_manifest.json` - 资源清单
- `fgui_spec.md` - FairyGUI 拼装规格
- `package.xml` - 包描述文件
- `*.xml` - 组件 XML 文件

## 验证命令速查

| 验证项 | 命令 |
|--------|------|
| 设计审批 | `python scripts/check_design_approval.py --root .` |
| XML 就绪 | `python scripts/check_xml_readiness.py --root . --profile fresh` |
| 资产隔离 | `python scripts/validate_asset_isolation.py --root . --stage asset_planning` |
| 组件复用 | `python scripts/validate_component_reuse.py --root . --stage fairygui_assembly` |
| 语义映射 | `python scripts/validate_semantic_controller_mapping.py --root . --stage xml_generation` |
| 视觉覆盖 | `python scripts/validate_visual_part_coverage.py --root . --stage xml_generation` |
| Z序验证 | `python scripts/validate_display_list_z_order.py --root . --stage xml_generation` |
| 字体保真 | `python scripts/validate_typography_fidelity.py --root . --stage xml_generation` |
| 血缘验证 | `python scripts/validate_production_preview_lineage.py --root . --stage asset_planning` |
| XML 验证 | `python scripts/validate_fgui_xml.py --root . --mode fresh` |
| 流水线验证 | `python scripts/validate_pipeline.py --root .` |
| 时序记录 | `python scripts/record_pipeline_timing.py --root . --start-stage requirement_intake` |

## 契约与规范

本项目通过契约文档确保各阶段的规范遵循：

- **Manifest Contract** - 资源清单的规范结构
- **Design Mockup Approval Contract** - 设计审批流程规范
- **Design to Layout Contract** - 设计到布局转换规范
- **Component Reuse Contract** - 组件复用策略规范
- **Visual Part Coverage Contract** - 视觉元素覆盖规范
- **Semantic Controller Mapping Contract** - 控制器语义映射规范
- **Display List Z-Order Contract** - 显示层级规范
- **Typography Fidelity Contract** - 字体渲染规范
- **Asset Isolation Contract** - 资源隔离规范
- **XML Strict Generation** - XML 严格生成规范

## 最佳实践

1. **前置审批**：在进入布局工作前，确保设计稿已获得明确批准
2. **语义优先**：在进行布局工作前，建立清晰的语义/状态映射
3. **严格模式**：在生成 package.xml 或组件 XML 前，强制启用 XML 严格模式
4. **持续验证**：每个阶段完成后执行相应的验证脚本
5. **文档驱动**：所有变更应反映在相应的规范文档中

## 常见问题

### Q: 如何添加新的验证规则？
A: 在 `references/` 目录下创建新的契约文档，然后在 `scripts/` 目录中实现对应的验证脚本。

### Q: 如何跳过某个验证阶段？
A: 某些关键验证（如设计审批）是强制性的，不应跳过。可选的验证可通过命令行参数控制。

### Q: 验证失败后如何处理？
A: 验证脚本会生成详细的 Markdown 报告，指出问题位置和修复建议。根据报告修改后重新运行验证。

### Q: 如何自定义输出模板？
A: 修改 `references/output-templates.md` 中的模板定义，确保新模板符合契约规范。

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交变更 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

## 许可证

本项目遵循 [LICENSE](LICENSE) 中指定的许可证。

## 参考资源

- [FairyGUI 官方文档](https://www.fairygui.com/)
- [FairyGUI XML 解析规范](references/fairygui-xml-parsing-specification.md)
- [AI 自动生成流程](references/fairygui-ai-generation-workflow.md)
