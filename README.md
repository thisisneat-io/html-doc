# html-doc-plugin

NEAT write plugin that generates a self-contained, interactive HTML documentation
file from any loaded NEAT physical data model.

---

## Install

Install in editable mode from the local folder:

    pip install -e path/to/html-doc-plugin

---

## Quick start

### Via the NEAT plugin framework (recommended)

Install the package and NEAT auto-discovers the plugin through the entry-point
cognite.neat.plugin.data_model.file_writers:

    from cognite.neat import NeatSession, get_cognite_client

    client = get_cognite_client('.env')
    neat = NeatSession(client)

    neat.physical_data_model.read.cdf('my_space', 'my_model', 'v1')
    neat.physical_data_model.write.html_doc('docs/model.html')
    # prints: Generated: .../docs/model.html

Optional kwargs: cdm=, idm=, erbose=True.

### Via attach_plugin() (session-aware, legacy helper)

ttach_plugin() monkey-patches the write object and captures the live
NeatSession so CDM and IDM are fetched from CDF automatically:

    from cognite.neat import NeatSession, get_cognite_client
    from html_doc import attach_plugin

    client = get_cognite_client('.env')
    neat = attach_plugin(NeatSession(client))

    neat.physical_data_model.read.cdf('my_space', 'my_model', 'v1')
    neat.physical_data_model.write.html_doc('docs/model.html')
    # prints: Generated: .../docs/model.html

---

## What the plugin generates

The output is a **single self-contained HTML file** that opens in any browser
with no server or extra files needed.

### Header

- **Title**: the data model name from the metadata `name` field.
- **Subtitle**: the canonical CDF identifier in the format
  `space:externalId (version=version)` matching what is stored in CDF.

### Statistics bar

Total view types, properties, relations, and industry domains in the model.

### Domain sections

Views are automatically categorised into industry domains based on ISO 14224,
CFIHOS, OSDU, SAP APM, and ISO 15288 naming conventions, for example
*Activities and Work Management*, *Location and Geography*, and
*Instrumentation and Control*. Each domain section contains one card per view type.

### View type cards

Each card shows:

- Display name, description, and which CDM type it implements (e.g. CogniteAsset).
- Own and inherited property counts.
- Full property table: own properties plus inherited properties with source indicated.
- Collapsible by default; expand individually or with Expand All / Collapse All.

### ER diagrams - five levels

| Level | Name | What it shows |
|-------|------|---------------|
| 1 | Domain Overview | All domain entities grouped by cluster, coloured by domain |
| 2 | Entity Focus | One diagram per entity: the entity, all direct incoming/outgoing relations, and its CDM parent |
| 3 | Domain Relationship Map | All domain entities and every data relation between them, no CDM nodes |
| 4 | Full Architecture with CDM | Domain entities plus the Cognite Core Data Model foundation they extend |
| 5 | All Relations incl. CDM Implements | Every domain entity, every data relation, and every implements arrow to a CDM type |

**Diagram interactivity:**

- Pan and zoom inside every diagram.
- Pop out any diagram into a full-screen overlay.
- Click any entity box to open its detail card.
- Hover over any entity box to highlight all connected relation lines;
  other lines are dimmed. Works in both inline and pop-out views.

### Search and theming

- A live search bar filters view cards across all domains instantly.
- A toggle in the header switches between dark and light mode; all diagrams
  re-render with appropriate colours.

---

## How CDM context is resolved

The Cognite Core Data Model (CDM) is needed for Level 4 and Level 5 diagrams,
the Entity Hierarchy, and for the implements annotation on each view card.
The plugin resolves it in this priority order:

**1. Explicit override**

Pass `cdm=path/to/CogniteCore.yaml` to use a specific file and skip all auto-detection.

**2. Live fetch from CDF (default, recommended)**

A separate, temporary NeatSession is created using the same CDF credentials.
It reads `cdf_cdm:CogniteCore v1` from CDF and exports it to a temporary YAML
file that is deleted after the HTML is written.
The loaded model in the calling session is never modified.
If the fetch fails for any reason (no connectivity, no permission) the plugin
silently falls through to the next option.

**3. Bundled fallback**

A copy of `CogniteCore.yaml` is shipped inside the plugin package and is used
when neither an explicit path nor a live fetch is available.

Note: the bundled fallback may lag behind the live CDF version.
Update it by copying a fresh `CogniteCore.yaml` into the `html_doc/` folder
and reinstalling with `pip install -e .`

---

## How IDM context is resolved

The Cognite Industrial Data Model (IDM, `CogniteProcessIndustries`) adds
industry-specific entity types on top of CDM and is used to populate the
*IDM Industry Types* tab and the Entity Hierarchy.
The plugin resolves it in the same priority order as CDM:

**1. Explicit override**

Pass `idm=path/to/CogniteProcessIndustries.yaml` to use a specific file.

**2. Live fetch from CDF (default, recommended)**

A separate, temporary NeatSession fetches `cdf_idm:CogniteProcessIndustries v1`
from CDF into a temporary YAML that is deleted after generation.

**3. Bundled fallback**

A copy of `CogniteProcessIndustries.yaml` is shipped inside the plugin package.

Note: the bundled fallback may lag behind the live CDF version.
Update it by copying a fresh `CogniteProcessIndustries.yaml` into the `browse_model/`
folder and reinstalling with `pip install -e .`

---

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| io | str or Path | required | Output path for the .html file |
| cdm | str or Path or None | None | Explicit CDM YAML path (`CogniteCore.yaml`), skips auto-fetch |
| idm | str or Path or None | None | Explicit IDM YAML path (`CogniteProcessIndustries.yaml`), skips auto-fetch |
| script_path | str or Path or None | None | Override path to generate_documentation_v7.py |
| verbose | bool | False | Print detailed progress; quiet by default |

---

## How it works internally

### Plugin framework path (HtmlDocPlugin / HtmlDocExporter)

1. NEAT discovers HtmlDocPlugin via the cognite.neat.plugin.data_model.file_writers
   entry-point when the package is installed.
2. When write.html_doc(io, **kwargs) is called, NEAT calls
   HtmlDocPlugin.configure(io=..., **kwargs), which returns a
   HtmlDocExporter instance.
3. NEAT calls HtmlDocExporter.export_to_file(data_model, file_path),
   passing the loaded RequestSchema and the output path.
4. export_to_file converts RequestSchema to a temporary YAML using
   DMSTableYamlExporter, resolves CDM and IDM, and calls
un_generation().
5. All temporary files are deleted.

### attach_plugin() path (legacy / session-aware helper)

1. ttach_plugin(neat_session) monkey-patches rowse_model() onto

eat.physical_data_model.write, capturing the session in a closure so
   CDM and IDM can be fetched live from CDF using the same credentials.
2. rowse_model() exports the loaded model to a temporary YAML and calls

un_generation() with both YAML paths.
3. All temporary files are deleted.

### Script resolution order for generate_documentation_v7.py

1. script_path= argument
2. NEAT_HTML_DOC_SCRIPT environment variable
3. Bundled copy inside the plugin package (primary)
4. ../NEAT_PROJECTS/ relative to the plugin folder
5. Current working directory
6. C:/neat/NEAT_PROJECTS/ as last resort

---

## Running the generator as a standalone script

`generate_documentation_v7.py` can also be invoked directly from the command
line without installing the plugin or connecting to CDF.  This is useful for
quickly generating docs from local files.

### Usage

    python generate_documentation_v7.py <input_file> [options]

### Arguments

| Argument | Description |
|----------|-------------|
| `input_file` | Path to the NEAT data model file (`.yaml`, `.yml`, or `.xlsx`) |
| `--cdm PATH` | Path to a local `CogniteCore.yaml` (Cognite Core Data Model). If omitted, a bundled copy is used. |
| `--idm PATH` | Path to a local `CogniteProcessIndustries.yaml` (Cognite Industrial Data Model). If omitted, a bundled copy is used. |
| `-o / --output PATH` | Output HTML file path. Defaults to `<input>.html` in the same folder. |

### Examples

Generate docs using only the input model (CDM and IDM resolved from bundled files):

    python generate_documentation_v7.py my_model.yaml

Provide explicit CDM and IDM files:

    python generate_documentation_v7.py my_model.yaml \
        --cdm path/to/CogniteCore.yaml \
        --idm path/to/CogniteProcessIndustries.yaml

Specify a custom output path:

    python generate_documentation_v7.py my_model.xlsx -o docs/my_model.html

On Windows (PowerShell), use `` ` `` for line continuation or write the
command on a single line:

    python generate_documentation_v7.py my_model.yaml --cdm CogniteCore.yaml --idm CogniteProcessIndustries.yaml -o docs/output.html
