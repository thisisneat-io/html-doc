# html-doc-plugin

NEAT write plugin that generates a self-contained, interactive HTML documentation
file from any loaded NEAT physical data model (v9 generator).

---

## Install

```bash
# From this repository (stable path at repo root)
pip install -e html-doc-plugin

# Or from the distributable zip
# unzip html-doc-plugin.zip && pip install -e html-doc-plugin
```

Requires `cognite-neat>=0.123.4` and `openpyxl>=3.0`.

---

## Quick start

### Via the NEAT plugin framework (recommended)

```python
from cognite.neat import NeatSession, get_cognite_client

client = get_cognite_client(".env")
neat = NeatSession(client)

neat.physical_data_model.read.cdf("my_space", "my_model", "v1")
neat.physical_data_model.write.html_doc("docs/model.html")
# prints: Generated: .../docs/model.html
```

Optional kwargs: `cdm=`, `idm=`, `ref_paths=`, `env_path=`, `verbose=True`.

### Via attach_plugin() (session-aware helper)

```python
from cognite.neat import NeatSession, get_cognite_client
from html_doc import attach_plugin

client = get_cognite_client(".env")
neat = attach_plugin(NeatSession(client))

neat.physical_data_model.read.cdf("my_space", "my_model", "v1")
neat.physical_data_model.write.html_doc("docs/model.html")
```

---

## What the plugin generates

Single self-contained **HTML** file (no server). Highlights in **v9**:

### View cards and properties

- Full `space:externalId(version=...)` subtitle on every view type.
- **View role badge**: Object view, Edge type, Reference type, or CDM type.
  - **Edge type** is assigned when the view’s **own** properties use a container with
    `Used For: edge` in the model’s **Containers** section (for example `TagDocRelation`).
    Object views that only appear as the start or end of an edge relation on another view
    (for example `DOCUMENT`) stay **Object view**, not Edge type.
  - If container metadata is missing, a view is treated as Edge type only when it is named
    as `edgeSource=…` on another view’s edge property—not when it is merely a relation target.
- Property tables label connection kind: **Direct**, **Edge**, **Reverse** badges.
- Inherited vs own properties; cross-space value types show target space when needed.

### ER diagrams (five levels)

| Level | Name | What it shows |
|-------|------|---------------|
| 1 | Domain Overview | Domain entities by industry cluster; **vertical layout** with per-space sub-clusters when governed spaces are present |
| 2 | Entity Focus | One diagram per entity with direct relations and CDM parent |
| 3 | Domain Relationship Map | Domain entities and data relations; **smart layout** (see below) |
| 4 | Full Architecture with CDM | Domain entities plus CDM foundation types |
| 5 | All Relations incl. CDM Implements | Data relations and implements links to CDM |

**Level 1 and Level 3 layout (v9):**

- Increased vertical spacing (`nodeSpacing` / `rankSpacing`) for readability.
- **Governed / multi-space models**: views grouped into per-space subgraphs with invisible spine links for consistent vertical flow.
- **Level 3**: If the combined diagram is under Mermaid's **500,000 character** limit, a single overview is shown. If it would exceed the limit, **per-space diagrams** are generated instead. When the combined diagram fits **and** multiple spaces exist, both the **overview** and **per-space** diagrams are included.

**Cross-space relations report:**

- Table of direct relations whose source and target live in **different spaces**, with counts per space pair (for governed multi-space models).

**Diagram legend:**

- Node shapes: Object (rectangle), Edge type (rounded oval on **all** levels including
  Overview and Level 2), Reference (dashed purple), CDM ghost (slate).
- Line styles: Direct, Edge, Reverse relations.

**Diagram interactivity:**

- Pan and zoom; full-screen pop-out.
- Click a node to open the view card.
- **Hover** a node to see view name and description tooltip; unrelated edges dim.
- **Find across all diagrams** (ER Diagrams tab): after diagrams render, use the search bar
  above the level sections. Type a view name, pick a match from the dropdown, then **Go**
  (or Enter). The matching diagram opens if needed, the node is highlighted, and the view
  is centered in the diagram viewport.
- **Find in this diagram**: each Level 1–5 ER diagram has its own search bar. Same workflow,
  scoped to that diagram only.
- **Overview** tab diagram: pan/zoom, click, and hover work as above; it does not include a
  per-diagram find bar (use ER Diagrams find or view-card search for Overview nodes).

### Entity Hierarchy, search, theming

- Collapsible CDM / IDM / domain tree with filter.
- Live search across view cards (Overview and Entity sections).
- Dark / light mode toggle.

---

## Governed spaces and reference models

Models with `governedSpaces` metadata (comma-separated CDF spaces) load additional reference YAML per space. Resolution order:

1. **`ref_paths=`** explicit YAML list
2. **Auto-discovery**: `governed_space_{space}.yaml` next to the input file (legacy: `{space}.yaml`)
3. **CDF fetch** via live `NeatSession` or `--env` / `env_path=`

Reference views appear in domain sections and ER diagrams (purple styling) when they match a domain category.

---

## CDM and IDM context

Resolved in priority order: explicit path -> live CDF fetch -> bundled `CogniteCore.yaml` / `CogniteProcessIndustries.yaml` in the package.

Update bundled files by copying fresh YAML into `html_doc/` and reinstalling: `pip install -e .`

---

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `io` | str or Path | required | Output `.html` path |
| `cdm` | str or Path or None | None | Explicit CDM YAML; skips auto-fetch |
| `idm` | str or Path or None | None | Explicit IDM YAML |
| `ref_paths` | list or None | None | Reference model YAML paths for governed spaces |
| `env_path` | str or Path or None | None | `.env` for CDF when no live session |
| `script_path` | str or Path or None | None | Override `generate_documentation_v9.py` |
| `version_override` | str or None | None | Toolkit `{{version}}` placeholder (e.g. `v1.0.0`) |
| `verbose` | bool | False | Progress messages |

---

## How it works internally

1. NEAT discovers `HtmlDocPlugin` via `cognite.neat.plugin.data_model.file_writers`.
2. Model is exported to temporary YAML (`DMSTableYamlExporter`).
3. Bundled **`generate_documentation_v9.py`** runs (or script from `NEAT_HTML_DOC_SCRIPT` / `script_path=`).
4. CDM, IDM, and reference models are resolved; temporaries are deleted.

Script resolution order:

1. `script_path=` argument
2. `NEAT_HTML_DOC_SCRIPT` environment variable
3. **Bundled** `html_doc/generate_documentation_v9.py` (primary)
4. `html-doc/html_doc/generate_documentation_v9.py` or `NEAT_PROJECTS/...` on disk
5. v8 / v7 fallbacks if present

---

## Standalone CLI (without NEAT session)

```bash
python generate_documentation_v9.py <input> [options]
```

`<input>`: NEAT `.yaml` / `.xlsx`, Toolkit `*.DataModel.yaml`, or module directory.

| Argument | Description |
|----------|-------------|
| `--cdm PATH` | CogniteCore.yaml |
| `--idm PATH` | CogniteProcessIndustries.yaml |
| `--ref YAML` | Reference model YAML (repeatable) |
| `--env ENV_FILE` | CDF credentials: fetch CDM/IDM when `--cdm`/`--idm` omitted; governed-space refs |
| `--version VERSION` | Toolkit template version when not in config |
| `--config CONFIG_YAML` | Toolkit config with `variables.version` |
| `-o / --output PATH` | Output HTML path |

Examples:

```bash
python generate_documentation_v9.py my_model.yaml --cdm html_doc/CogniteCore.yaml -o docs/model.html

python generate_documentation_v9.py path/to/ssp_supply_chain --version v1.0.0 --env .env -o isc.html
```

---

## Package contents

```
html-doc-plugin/
├── pyproject.toml
├── README.md
└── html_doc/
    ├── plugin.py              # NEAT entry point
    ├── _exporter.py           # HtmlDocExporter
    ├── _writer.py             # attach_plugin + script resolution
    ├── generate_documentation_v9.py
    ├── CogniteCore.yaml       # bundled CDM fallback
    └── CogniteProcessIndustries.yaml
```

---

## Version history

| Version | Generator | Notes |
|---------|-----------|-------|
| 0.2.1 | v9 | Global + per-diagram ER find (pan/zoom to match); edge type from `Used For: edge` containers; oval edge nodes on Overview and L2 |
| 0.2.0 | v9 | L1/L3 layout, governed-space clusters, conditional L3 split, cross-space report, legend, hover tooltips, view/connection badges |
| 0.1.x | v8 | Initial plugin packaging |
