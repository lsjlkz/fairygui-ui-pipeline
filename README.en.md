# FairyGUI UI Pipeline

Semi-automated Game UI Production Pipeline

## Overview

FairyGUI UI Pipeline is a comprehensive game UI production solution designed to convert UI requirements, design drafts, and image resources into usable resource packages compliant with FairyGUI specifications. This pipeline adopts a **semi-automated** design, combining manual review with automated verification to ensure a balance between UI production quality and efficiency.

## Core Functions

### 📋 Full Process Management
- **Requirement Intake**: Structured requirement collection and confirmation
- **UX/UI Specifications**: Semantically defined UI specifications
- **Visual Design Brief**: Clear definition of design goals and constraints
- **Full-screen Mockup Generation**: AI-assisted design draft generation
- **Manual Review Approval**: Mandatory design review process
- **Semantic Analysis**: Semantic mapping from requirements to design
- **Layout Analysis**: Conversion from design to layout
- **Asset Planning**: Image resources and texture sheet planning
- **Image Generation**: Production-ready image resource generation
- **Texture Sheet Slicing**: Optimized slicing schemes
- **FairyGUI Assembly Planning**: Component-based assembly strategy
- **Resource Staging**: Stage management of package resources
- **XML Draft Generation**: Specification-compliant XML output
- **Multi-dimensional Validation**: Multi-level quality validation
- **Editor Publishing**: Unity integration preparation
- **Smoke Testing**: Runtime verification
- **Timeline Finalization**: Final delivery confirmation

### 🔒 Strict Mode
- **XML Strict Mode**: Mandatory XML specification checks
- **Design Approval Gate**: Full-screen mockups must undergo manual approval
- **Semantic Mapping Gate**: Semantic correspondence between states and controllers must be explicit
- **Asset Isolation**: Strict separation of visual assets and logical assets

### ✅ Automated Validation
- **Resource Provenance Validation**: Ensure resource sources are clear and traceable
- **Component Reuse Validation**: Detect duplication and reuse opportunities
- **Semantic Controller Mapping**: Verify correspondence between controllers and UI states
- **Visual Part Coverage**: Completeness of visual elements in UI components
- **Display List Z-Order**: Verification of hierarchy structure correctness
- **Typography Fidelity**: Consistency verification of text rendering
- **Asset Isolation Compliance**: Detection of adherence to isolation specifications
- **Production Preview Lineage**: Tracking verification of resource derivation

## Directory Structure

```
fairygui-ui-pipeline/
├── SKILL.md                    # Skill Description Document
├── USAGE.md                    # User Guide (English)
├── agents/                     # Agent Configuration
│   └── openai.yaml
├── references/                 # Specifications & Contract Documents
│   ├── pipeline.md             # Pipeline Definition
│   ├── fairygui-xml-parsing-specification.md  # XML Parsing Specification
│   ├── fairygui-ai-generation-workflow.md     # AI Auto-generation Workflow
│   ├── manifest-contract.md    # Manifest Contract
│   ├── design-mockup-approval-contract.md     # Design Approval Contract
│   ├── design-to-layout-contract.md           # Design to Layout Contract
│   ├── component-reuse-parameterization-contract.md  # Component Reuse Contract
│   ├── visual-part-coverage-contract.md       # Visual Part Coverage Contract
│   ├── semantic-controller-mapping-contract.md # Semantic Controller Mapping Contract
│   ├── display-list-z-order-contract.md       # Display List Z-Order Contract
│   ├── typography-fidelity-contract.md        # Typography Fidelity Contract
│   ├── asset-isolation-contract.md            # Asset Isolation Contract
│   ├── production-preview-lineage-contract.md  # Production Preview Lineage Contract
│   ├── visual-reference-contract.md           # Visual Reference Contract
│   ├── component-instance-configuration-contract.md  # Component Instance Configuration Contract
│   ├── asset-size-contract.md                 # Asset Size Contract
│   ├── bitmap-icon-source-contract.md         # Bitmap Icon Source Contract
│   ├── package-resource-path-contract.md      # Package Resource Path Contract
│   ├── pipeline-stage-timing-contract.md      # Pipeline Timing Contract
│   ├── xml-strict-generation.md               # XML Strict Generation
│   ├── output-templates.md                    # Output Templates
│   └── embedded-docs-manifest.json            # Embedded Docs Manifest
├── scripts/                   # Validation & Tool Scripts
│   ├── check_design_approval.py        # Design Approval Check
│   ├── check_xml_readiness.py          # XML Readiness Check
│   ├── image_metadata.py               # Image Metadata Reader
│   ├── record_design_approval.py       # Record Design Approval
│   ├── record_pipeline_timing.py       # Record Pipeline Timing
│   ├── record_production_preview_approval.py  # Record Production Preview Approval
│   ├── validate_asset_isolation.py     # Validate Asset Isolation
│   ├── validate_bitmap_asset_provenance.py    # Validate Asset Provenance
│   ├── validate_component_reuse.py     # Validate Component Reuse
│   ├── validate_display_list_z_order.py      # Validate Z-Order
│   ├── validate_fgui_xml.py            # Validate FairyGUI XML
│   ├── validate_pipeline.py            # Validate Pipeline
│   ├── validate_production_preview_lineage.py # Validate Lineage
│   ├── validate_semantic_controller_mapping.py # Validate Semantic Mapping
│   ├── validate_typography_fidelity.py # Validate Typography Fidelity
│   ├── validate_visual_part_coverage.py      # Validate Visual Coverage
│   └── verify_embedded_docs.py         # Verify Embedded Docs
└── tests/                       # Unit Tests
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

## Quick Start

### Prerequisites

- Python 3.8+
- FairyGUI Editor (for publishing and testing)
- Unity 2020+ (for integration testing)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd fairygui-ui-pipeline
```

2. Install dependencies (if required):
```bash
pip install -r requirements.txt
```

### Basic Usage Flow

#### 1. Create Project Structure
Create necessary specification documents according to the templates in `references/output-templates.md`.

#### 2. Run Design Approval
```bash
python scripts/record_design_approval.py --root /path/to/project --approve design.png
```

#### 3. Validate Asset Isolation
```bash
python scripts/validate_asset_isolation.py --root /path/to/project --stage asset_planning
```

#### 4. Generate XML Strict Mode
```bash
python scripts/check_xml_readiness.py --root /path/to/project --profile fresh
```

#### 5. Validate Final Output
```bash
python scripts/validate_fgui_xml.py --root /path/to/project --mode fresh
```

## Pipeline Stage Details

| Stage | ID | Description |
|------|-----|------|
| Requirement Intake | `requirement_intake` | Collect and confirm UI requirements |
| UX/UI Specifications | `uxui_spec` | Define semantically defined UI specifications |
| Visual Design Brief | `visual_design_brief` | Clarify design goals and constraints |
| Full-screen Design Generation | `full_screen_design` | AI-assisted design draft generation |
| Design Approval | `design_approval` | Manual approval of design drafts |
| Semantic Analysis | `semantic_analysis` | Semantic mapping of requirements and design |
| Layout Analysis | `layout_analysis` | Conversion from design to layout |
| Asset Planning | `asset_planning` | Image resource planning |
| Image Generation | `image_generation` | Production-grade image generation |
| Texture Sheet Slicing | `sheet_slice` | Optimized slicing scheme |
| Assembly Planning | `fgui_assembly` | Component-based assembly strategy |
| Resource Staging | `resource_stage` | Stage management of package resources |
| XML Generation | `xml_generation` | XML draft generation |
| Quality Validation | `validation` | Multi-dimensional quality validation |
| Editor Publishing | `editor_publish` | Unity integration preparation |
| Smoke Testing | `smoke_test` | Runtime verification |
| Final Handoff | `final_handoff` | Final delivery confirmation |

## Output Artifacts

The pipeline stages produce the following artifacts:

- `ui_spec.md` - UI Specification Document
- `visual_design_brief.md` - Visual Design Brief
- `design_approval.json` - Design Approval Record
- `uxui_semantic_spec.md` - Semantic Specification Document
- `layout_spec.json` - Layout Specification
- `asset_manifest.json` - Asset Manifest
- `fgui_spec.md` - FairyGUI Assembly Specification
- `package.xml` - Package Description File
- `*.xml` - Component XML Files

## Verification Commands Quick Reference

| Validation Item | Command |
|--------|------|
| Design Approval | `python scripts/check_design_approval.py --root .` |
| XML Readiness | `python scripts/check_xml_readiness.py --root . --profile fresh` |
| Asset Isolation | `python scripts/validate_asset_isolation.py --root . --stage asset_planning` |
| Component Reuse | `python scripts/validate_component_reuse.py --root . --stage fairygui_assembly` |
| Semantic Mapping | `python scripts/validate_semantic_controller_mapping.py --root . --stage xml_generation` |
| Visual Coverage | `python scripts/validate_visual_part_coverage.py --root . --stage xml_generation` |
| Z-Order Validation | `python scripts/validate_display_list_z_order.py --root . --stage xml_generation` |
| Typography Fidelity | `python scripts/validate_typography_fidelity.py --root . --stage xml_generation` |
| Lineage Validation | `python scripts/validate_production_preview_lineage.py --root . --stage asset_planning` |
| XML Validation | `python scripts/validate_fgui_xml.py --root . --mode fresh` |
| Pipeline Validation | `python scripts/validate_pipeline.py --root .` |
| Timing Recording | `python scripts/record_pipeline_timing.py --root . --start-stage requirement_intake` |

## Contracts & Specifications

This project ensures stage compliance through contract documents:

- **Manifest Contract** - Specification structure for asset manifests
- **Design Mockup Approval Contract** - Design approval process specifications
- **Design to Layout Contract** - Design to layout conversion specifications
- **Component Reuse Contract** - Component reuse strategy specifications
- **Visual Part Coverage Contract** - Visual element coverage specifications
- **Semantic Controller Mapping Contract** - Controller semantic mapping specifications
- **Display List Z-Order Contract** - Display hierarchy specifications
- **Typography Fidelity Contract** - Font rendering specifications
- **Asset Isolation Contract** - Resource isolation specifications
- **XML Strict Generation** - XML strict generation specifications

## Best Practices

1. **Pre-approval**: Ensure design drafts have received clear approval before starting layout work.
2. **Semantics First**: Establish clear semantic/state mappings before performing layout work.
3. **Strict Mode**: Enforce XML strict mode before generating `package.xml` or component XML files.
4. **Continuous Validation**: Execute corresponding validation scripts after each stage completion.
5. **Documentation Driven**: All changes should be reflected in the relevant specification documents.

## Frequently Asked Questions

### Q: How to add new validation rules?
A: Create a new contract document in the `references/` directory, then implement the corresponding validation script in the `scripts/` directory.

### Q: How to skip a validation stage?
A: Some critical validations (such as design approval) are mandatory and should not be skipped. Optional validations can be controlled via command-line arguments.

### Q: What to do after a validation failure?
A: The validation script generates a detailed Markdown report indicating the problem location and repair suggestions. Modify according to the report and re-run the validation.

### Q: How to customize output templates?
A: Modify the template definitions in `references/output-templates.md`, ensuring the new templates comply with contract specifications.

## Contribution Guide

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project follows the license specified in [LICENSE](LICENSE).

## References

- [FairyGUI Official Documentation](https://www.fairygui.com/)
- [FairyGUI XML Parsing Specification](references/fairygui-xml-parsing-specification.md)
- [AI Auto-generation Workflow](references/fairygui-ai-generation-workflow.md)
