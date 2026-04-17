from __future__ import annotations

import contextlib
import io as _io
import tempfile
from pathlib import Path
from typing import Any

from cognite.neat._data_model.exporters import DMSFileExporter
from cognite.neat._data_model.models.dms import RequestSchema

from ._writer import (
    _BUNDLED_CDM,
    _BUNDLED_IDM,
    _fetch_cdm_yaml,
    _fetch_idm_yaml,
    _find_gen_script,
    _import_run_generation,
)


class HtmlDocExporter(DMSFileExporter):
    """DMSFileExporter that generates interactive HTML documentation.

    Returned by HtmlDocPlugin.configure(). NEAT calls export_to_file()
    with the loaded RequestSchema and the user-supplied output path.

    Parameters
    ----------
    io : str or Path or None
        Default output path used by export(). Overridden by export_to_file file_path.
    cdm : str or Path or None
        Explicit path to CogniteCore.yaml. Bundled fallback used when omitted.
    idm : str or Path or None
        Explicit path to CogniteProcessIndustries.yaml. Same fallback logic.
    script_path : str or Path or None
        Explicit path to generate_documentation_v7.py (auto-detected otherwise).
    verbose : bool
        Print progress messages when True.
    neat_session : object or None
        A live NeatSession for fetching CDM/IDM from CDF.
        Not injected by the plugin framework; use attach_plugin() for that.
    """

    def __init__(
        self,
        io=None,
        cdm=None,
        idm=None,
        script_path=None,
        verbose=False,
        neat_session=None,
        **_ignored,
    ):
        self._output_path = Path(io).resolve() if io else None
        self._cdm = Path(cdm) if cdm else None
        self._idm = Path(idm) if idm else None
        self._script_path = script_path
        self._verbose = verbose
        self._neat_session = neat_session

    def export(self, data_model):
        """Write HTML to the configured output path and return that path."""
        if self._output_path is None:
            raise ValueError(
                "No output path set. Pass io= to configure() or call export_to_file() directly."
            )
        self.export_to_file(data_model, self._output_path)
        return self._output_path

    def export_to_file(self, data_model, file_path):
        """Generate interactive HTML documentation from data_model."""
        from cognite.neat._data_model.exporters import DMSTableYamlExporter

        file_path = Path(file_path).resolve()
        file_path.parent.mkdir(parents=True, exist_ok=True)

        verbose = self._verbose
        sink = (
            contextlib.nullcontext()
            if verbose
            else contextlib.redirect_stdout(_io.StringIO())
        )

        cdm_tmp_path = None
        idm_tmp_path = None

        with tempfile.TemporaryDirectory() as _tmp:
            tmp_dir = Path(_tmp)
            tmp_yaml = tmp_dir / "_html_doc_input_.yaml"
            try:
                yaml_exporter = DMSTableYamlExporter()
                with sink:
                    yaml_exporter.export_to_file(data_model, tmp_yaml)

                if not tmp_yaml.exists() or tmp_yaml.stat().st_size == 0:
                    raise RuntimeError(
                        "YAML export produced an empty file. "
                        "Ensure a data model is loaded before calling write.browse_model()."
                    )

                if self._cdm:
                    cdm_path = self._cdm
                elif self._neat_session is not None:
                    fetched = _fetch_cdm_yaml(
                        self._neat_session, tmp_dir, verbose=verbose
                    )
                    if fetched and fetched != _BUNDLED_CDM:
                        cdm_tmp_path = fetched
                    cdm_path = fetched
                else:
                    cdm_path = _BUNDLED_CDM if _BUNDLED_CDM.exists() else None

                if self._idm:
                    idm_path = self._idm
                elif self._neat_session is not None:
                    fetched_idm = _fetch_idm_yaml(
                        self._neat_session, tmp_dir, verbose=verbose
                    )
                    if fetched_idm and fetched_idm != _BUNDLED_IDM:
                        idm_tmp_path = fetched_idm
                    idm_path = fetched_idm
                else:
                    idm_path = _BUNDLED_IDM if _BUNDLED_IDM.exists() else None

                gen_script = _find_gen_script(self._script_path)
                if verbose:
                    print("[html_doc] Using script: " + str(gen_script))

                run_gen = _import_run_generation(gen_script)
                with sink:
                    run_gen(
                        input_path=tmp_yaml,
                        output_path=file_path,
                        cdm_path=cdm_path,
                        idm_path=idm_path,
                    )

                label = "[html_doc] Generated: " if verbose else "Generated: "
                print(label + str(file_path))

            finally:
                if cdm_tmp_path and cdm_tmp_path.exists():
                    cdm_tmp_path.unlink()
                if idm_tmp_path and idm_tmp_path.exists():
                    idm_tmp_path.unlink()
