# Plasticity Houdini Bridge development plan

## Goal

Create a pull-based Plasticity-to-Houdini mesh bridge. A user configures a
Python Snippet or classic Python SOP, then presses **Update Plasticity** to
request a snapshot from Plasticity and replace the SOP output. The bridge is
not a persistent live link and does not upload Houdini geometry to Plasticity.

## User workflow

1. Install this repository as a Houdini package.
2. Create a **Python Snippet** SOP or a classic **Python** SOP.
3. Paste the matching wrapper from `scripts/python/sop/`, select the SOP, and
   run the shelf setup script.
4. Configure the Plasticity server (normally `localhost:8980`) and import
   controls.
5. Press **Update Plasticity** whenever the Plasticity scene or bridge
   settings should be re-fetched.

The button increments a hidden update generation and force-cooks the SOP. The
ordinary spare parameters have no Python Snippet bindings, so editing them does
not make a network request or recook the node.

## Scope

### Version 1

- WebSocket handshake with Plasticity.
- One-shot `LIST_VISIBLE` and `LIST_ALL` snapshot requests.
- Solid and sheet mesh import.
- Houdini polygons, vertex normals, object/group/face identity attributes, and
  detail provenance attributes.
- Optional `REFACET_SOME` flow for all fetched mesh objects.
- A Python Snippet wrapper, a classic Python SOP wrapper, and an idempotent
  shelf parameter installer.

### Deliberately excluded from version 1

- Live subscriptions and automatic scene updates.
- Houdini-to-Plasticity upload (`PUT_SOME`).
- Blender edit-mode utilities such as seam marking and face painting.
- Plasticity instance preservation. The current public bridge source does not
  decode an instance object type or instance transforms; future protocol
  support can map naturally to packed Houdini prototypes and transform points.

## Blender bridge feature audit

| Area | Blender bridge behavior | Houdini decision |
|---|---|---|
| Connection | Configurable WebSocket client, default `localhost:8980` | Include |
| Capability handshake | Reads supported message IDs | Include |
| Snapshot | List all or visible objects | Include |
| Live update | Subscribe/unsubscribe all, transaction processing | Exclude |
| Re-faceting | Re-facet selected Plasticity IDs | Include as optional update mode |
| Facet controls | Triangle/ngon, basic and advanced tolerances | Include |
| Source mesh data | Positions, faces, normals, face groups, face IDs | Include |
| Scene grouping | Object IDs, group IDs, parent IDs, names | Preserve as attributes |
| Upload | Send Blender meshes and collections to Plasticity | Exclude |
| Blender utilities | Face-ID selection, edge/seam marking, UV seam merge, color paint | Exclude/defer |

The Blender bridge has protocol support for `SOLID`, `SHEET`, `WIRE`, `GROUP`,
and `EMPTY`. Version 1 imports only solids and sheets because those are the
object types whose facet payload is decoded by the reference bridge.

## Node interface

### Connection/update

| Token | Label | Default |
|---|---|---|
| `server` | Plasticity Server | `localhost:8980` |
| `scope` | Fetch Scope | Visible |
| `update_mode` | Update Mode | Snapshot |
| `update_plasticity` | Update Plasticity | button |
| `timeout_seconds` | Timeout Seconds | 15 |
| `update_generation` | Update Generation | hidden, 0 |
| `verbose` | Verbose Diagnostics | off |

### Import metadata

| Token | Label | Default |
|---|---|---|
| `unit_scale` | Unit Scale | 1.0 |
| `import_solids` | Import Solids | on |
| `import_sheets` | Import Sheets | on |
| `import_normals` | Import Vertex Normals | on |
| `create_object_id` | Create Object ID Attribute | on |
| `create_face_id` | Create Plasticity Face ID Attribute | on |
| `create_group_id` | Create Face Group Attribute | on |
| `create_names` | Create Object Name Attribute | on |
| `create_parent_id` | Create Parent ID Attribute | on |

### Re-faceting

| Token | Label | Default |
|---|---|---|
| `facet_type` | Facet Type | Triangles |
| `facet_settings_mode` | Faceting Settings | Simple |
| `facet_tolerance` | Tolerance | 0.01 |
| `facet_angle` | Angle (radians) | 0.45 |
| `relative_to_bbox` | Relative to Bounding Box | on |
| `match_topology` | Match Topology | on |
| `curve_chord_tolerance` | Edge Chord Tolerance | 0.01 |
| `curve_chord_angle` | Edge Angle Tolerance | 0.45 |
| `surface_plane_tolerance` | Face Plane Tolerance | 0.01 |
| `surface_plane_angle` | Face Angle Tolerance | 0.45 |
| `facet_min_width` | Minimum Width | 0 |
| `facet_max_width` | Maximum Width | 0 |
| `plane_angle` | Plane Angle (radians) | 0.785398 |

`Snapshot` requests a direct list. `Snapshot Then Re-facet` first requests a
snapshot to discover object IDs, then requests re-faceted payloads for the
eligible solid/sheet IDs.

## Houdini output contract

| Class | Attribute | Meaning |
|---|---|---|
| Vertex | `N` | Plasticity corner normal |
| Primitive | `plasticity_id` | Stable Plasticity object ID |
| Primitive | `plasticity_version` | Object version |
| Primitive | `plasticity_face_id` | Original CAD-face ID |
| Primitive | `plasticity_face_group` | Facet group index |
| Primitive | `name` | Plasticity object name |
| Primitive | `plasticity_parent_id` | Parent/group ID |
| Primitive | `plasticity_material_id` | Source material ID |
| Primitive | `plasticity_flags` | Source flags |
| Detail | `plasticity_filename` | Plasticity document name |
| Detail | `plasticity_file_version` | Document version |
| Detail | `plasticity_server` | Source server |
| Detail | `plasticity_import_stats` | Import summary |

## Implementation stages

1. **Bootstrap**: repository package, SOP wrappers, idempotent spare parameter
   setup, explicit update callback.
2. **Protocol**: binary readers/writers, WebSocket handshake and frames,
   capability handshake, one-shot visible snapshot.
3. **Geometry**: convert decoded records to `hou.Geometry` using batch point
   and polygon methods; import metadata and normals.
4. **Feature completion**: all-scope snapshots, optional re-faceting, precise
   warnings for unsupported server features and object types.
5. **Validation**: protocol fixtures, mock-server tests, and manual Houdini
   tests with empty scenes, groups, sheets, hidden objects, large meshes,
   disconnects, and changed faceting settings.
6. **Future work**: packed hierarchy/instances once the protocol provides
   instance messages; viewport face-ID visualization; optional utility SOPs.

## Technical decisions

- Keep the network operation synchronous for version 1 because it happens only
  on a deliberate button click. This avoids unsafe background access to Houdini
  geometry. A later asynchronous implementation can put decoded records on a
  queue and build geometry on Houdini's main thread.
- Use only the standard Python library for the initial WebSocket client so the
  package has no external runtime dependency.
- Treat unsupported messages, malformed packets, and non-200 request replies
  as explicit Houdini errors, never silently empty geometry.
- Preserve all source IDs in the output, even when the initial HDA does not
  expose a direct editing utility for them.
