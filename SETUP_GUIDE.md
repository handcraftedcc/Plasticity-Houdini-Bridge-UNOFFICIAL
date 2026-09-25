# Plasticity Houdini Bridge setup

## 1. Install the Houdini package

Copy `PlasticityHoudiniBridge.json` into your Houdini preferences package
directory, for example:

```text
C:/Users/<you>/Documents/houdini21.0/packages/PlasticityHoudiniBridge.json
```

Edit its `PLASTICITYBRIDGE` value to the absolute repository path, using
forward slashes:

```json
{
    "enable": true,
    "env": [
        {
            "PLASTICITYBRIDGE": "C:/path/to/Plasticity Houdini Bridge"
        }
    ],
    "path": "$PLASTICITYBRIDGE"
}
```

Restart Houdini after saving the package file. This loads the Plasticity Bridge
HDA and its supporting Python package.

## 2. Create and use the HDA

1. Enter a Geometry network.
2. Press Tab and create a **Plasticity Bridge** SOP.
3. Set **Plasticity Server** to the bridge address, normally
   `localhost:8980`.
4. Choose **Fetch Scope** (`Visible` or `All`) and configure scale, import,
   and faceting controls as needed.
5. Press **Update Plasticity**.

The node connects, performs a capability handshake, requests the selected
snapshot, and outputs Houdini polygons. It is deliberately pull-based: editing
parameters does not contact Plasticity. A new request occurs only when the
button is pressed.

Use **Faceting Settings** to choose Simple (Tolerance and Angle) or Advanced
(separate edge and surface controls). Select **Snapshot Then Re-facet** in
**Update Mode** for those faceting settings to be sent to Plasticity.

## Output attributes

The output includes vertex normal `N` when enabled, plus primitive attributes:

- `plasticity_id`, `plasticity_version`
- `plasticity_face_id`, `plasticity_face_group`
- `plasticity_parent_id`, `plasticity_material_id`, `plasticity_flags`
- `name`

Detail attributes identify the document, file version, source server, and
import statistics.

## Development-only Python builders

The HDA is the complete user-facing interface. The Python Snippet/Python SOP
wrappers and the shelf parameter installer in `scripts/python/` are retained
only to build, inspect, or develop the HDA. End users do not need to paste
Python code or create a shelf tool.

## Troubleshooting

- **`No connection could be made` / connection refused**: Plasticity is not
  listening at the configured address. Verify the bridge is enabled and that
  its actual host and port match **Plasticity Server**.
- **`Plasticity server does not support List Visible/All`**: use a Plasticity
  build with the current bridge protocol enabled.
- **ModuleNotFoundError**: restart Houdini and verify the package JSON uses
  the correct absolute repository path and `"path": "$PLASTICITYBRIDGE"`.
- **No output**: use `All` once to rule out visibility filtering, and confirm
  the active Plasticity document contains solids or sheets.

The first version imports Plasticity solids and sheets only. It does not use a
live subscription, upload Houdini geometry, or preserve Plasticity instances.
