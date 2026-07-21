# Package Resource Path Contract

Use this contract whenever assets are staged into `fgui_xml/<package>/`, `package.xml` is generated, component XML uses `fileName`, or a package is copied into a FairyGUI project.

## Core Rule

Project-relative asset paths and FairyGUI-package-relative resource paths are different coordinate systems.

```text
UIProduction root-relative path:
fgui_xml/twinbound_v2/art/icon_anvil.png

FairyGUI package root:
fgui_xml/twinbound_v2/

package-relative file:
art/icon_anvil.png
```

Never write the UIProduction-root-relative path directly into `package.xml` or component XML.

## Manifest Fields

Every bitmap or other file-backed FairyGUI resource must contain:

- `file`: path relative to the `UIProduction` root.
- `packageRelativeFile`: path relative to `package.outputPath`.

Example:

```json
{
  "package": {
    "name": "twinbound_v2",
    "outputPath": "fgui_xml/twinbound_v2"
  },
  "assets": [
    {
      "name": "icon_anvil",
      "file": "fgui_xml/twinbound_v2/art/icon_anvil.png",
      "packageRelativeFile": "art/icon_anvil.png"
    }
  ]
}
```

The following equality must hold after path normalization:

```text
asset.file == package.outputPath + "/" + asset.packageRelativeFile
```

`packageRelativeFile` must:

- use `/` separators
- be relative, not absolute
- not begin with `./` or `/`
- not contain `..`
- point to a real file inside the package output directory

## package.xml Mapping

For `packageRelativeFile = art/icon_anvil.png`, generate either of these equivalent package-local forms:

```xml
<image id="ia2r1" name="icon_anvil.png" path="/art/"/>
```

or:

```xml
<image id="ia2r1" name="art/icon_anvil.png" path="/"/>
```

Prefer the first form for consistency with existing FairyGUI projects.

The exact resource path represented by `path + name` must equal `packageRelativeFile` and must exist under the directory containing `package.xml`.

Do not generate:

```xml
<image name="fgui_xml/twinbound_v2/art/icon_anvil.png" path="/"/>
```

That path is relative to `UIProduction`, not relative to the FairyGUI package, and will appear as a missing/red resource in FairyGUI Editor.

## Component XML Mapping

For same-package `<image>` nodes, `fileName` must equal the exact `packageRelativeFile`:

```xml
<image src="ia2r1" fileName="art/icon_anvil.png" .../>
```

Do not accept basename-only equality during fresh generation. These are not equivalent:

```text
art/icon_anvil.png
fgui_xml/twinbound_v2/art/icon_anvil.png
some_other_folder/icon_anvil.png
```

For loaders using `ui://`, the URL must resolve to the resource whose `package.xml path + name` equals the declared `packageRelativeFile`.

## Package Staging Gate

Before XML generation or import:

1. create `package.outputPath`
2. copy or generate every resource to `package.outputPath/packageRelativeFile`
3. verify the staged file exists
4. generate `package.xml` from `packageRelativeFile`
5. generate component `fileName` from `packageRelativeFile`
6. validate `package.xml path + name` against the real package directory
7. only then copy the complete package directory into `GameUI/assets/<package>` or another FairyGUI project

Copy the entire package directory atomically. Do not copy XML and image files through independent incomplete lists.

## Blocking Conditions

Block editor import when:

- `packageRelativeFile` is missing
- `file` is not under `package.outputPath`
- `file` and `packageRelativeFile` describe different destinations
- a staged file is missing
- `package.xml path + name` does not resolve to the staged file
- component `image@fileName` differs from `packageRelativeFile`
- a registered/exported component XML file is missing
- the imported package directory differs from the validated staging directory

## Required Validation

`validate_fgui_xml.py` must validate exact package-local paths. Matching only by basename is forbidden in `fresh` mode.

The package may be called editor-ready only when all package resources resolve from the directory containing `package.xml`.
