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

Restart Houdini after saving the package file. This makes
`plasticity_houdini_bridge` importable from Houdini Python.

## 2. Create the node

1. Enter a Geometry network.
2. Create a **Python Snippet** SOP.
3. Open its **Python Code** parameter and paste this exact code:

```python
from plasticity_houdini_bridge.sop import cook_python_snippet

return cook_python_snippet(hou.pwd())
```

The same code is available in
`scripts/python/sop/plasticity_fetch.py`.

## 3. Create the bridge parameters

Select the Python Snippet SOP, then run this as a Houdini Shelf Tool:

```python
from plasticity_houdini_bridge.parameter_ui import configure_selected_nodes

configure_selected_nodes()
```

The source version is
`scripts/python/shelf/create_plasticity_fetch_parameters.py`.

To create the Shelf Tool:

1. In Houdini, click the `+` on the shelf and choose **New Tool**.
2. Give it a name such as `Configure Plasticity Fetch`.
3. Set **Script Language** to Python.
4. Paste the two-line script above into the Script tab and save it.
5. With one or more Python Snippet or classic Python SOP nodes selected, click
   the tool.

The installer is safe to run again: it preserves existing values and only adds
missing bridge parameters.

## 4. Fetch Plasticity geometry

On the configured SOP:

1. Set **Plasticity Server** to the server address, normally
   `localhost:8980`.
2. Choose **Fetch Scope**: `Visible` or `All`.
3. Set **Unit Scale** if the incoming model needs scaling.
   Use **Faceting Settings** to choose Simple (Tolerance and Angle) or
   Advanced (separate edge and surface controls).
4. Press **Update Plasticity**.

The node connects, performs a capability handshake, requests the selected
snapshot, and outputs Houdini polygons. It is deliberately pull-based: editing
parameters does not contact Plasticity. A new request occurs only when the
button is pressed.

## Output attributes

The output includes vertex normal `N` when enabled, plus primitive attributes:

- `plasticity_id`, `plasticity_version`
- `plasticity_face_id`, `plasticity_face_group`
- `plasticity_parent_id`, `plasticity_material_id`, `plasticity_flags`
- `name`

Detail attributes identify the document, file version, source server, and
import statistics.

## Classic Python SOP alternative

For a classic **Python** SOP, select it and run the same shelf tool. If its
Python Code field is empty, the setup tool installs the correct wrapper. You
can also paste this manually:

```python
from plasticity_houdini_bridge.sop import cook_python_sop

cook_python_sop(hou.pwd())
```

## Troubleshooting

- **`No connection could be made` / connection refused**: Plasticity is not
  listening at the configured address. Verify the bridge is enabled and that
  its actual host and port match **Plasticity Server**. The local bridge test
  currently found no listener on `localhost:8980`.
- **`Plasticity server does not support List Visible/All`**: use a Plasticity
  build with the current bridge protocol enabled.
- **ModuleNotFoundError**: restart Houdini and verify the package JSON uses
  the correct absolute repository path and `"path": "$PLASTICITYBRIDGE"`.
- **No output**: use `All` once to rule out visibility filtering, and confirm
  the active Plasticity document contains solids or sheets.

The first version imports Plasticity solids and sheets only. It does not use a
live subscription, upload Houdini geometry, or preserve Plasticity instances.
