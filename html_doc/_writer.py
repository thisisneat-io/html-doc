from __future__ import annotations
import contextlib, io as _io, os, sys, tempfile
from pathlib import Path

# ── Bundled paths ────────────────────────────────────────────────────────────
_PKG_DIR = Path(__file__).parent
_BUNDLED_SCRIPT = _PKG_DIR / 'generate_documentation_v7.py'
_BUNDLED_CDM    = _PKG_DIR / 'CogniteCore.yaml'
_BUNDLED_IDM    = _PKG_DIR / 'CogniteProcessIndustries.yaml'


def _find_gen_script(hint=None):
    """Locate generate_documentation_v7.py, preferring bundled copy."""
    candidates = []
    if hint:
        candidates.append(Path(hint))
    env = os.environ.get('NEAT_HTML_DOC_SCRIPT')
    if env:
        candidates.append(Path(env))
    candidates += [
        _BUNDLED_SCRIPT,                                           # bundled (primary)
        Path(__file__).parent.parent.parent / 'NEAT_PROJECTS' / 'generate_documentation_v7.py',
        Path.cwd() / 'NEAT_PROJECTS' / 'generate_documentation_v7.py',
        Path.cwd() / 'generate_documentation_v7.py',
        Path('C:/neat/NEAT_PROJECTS/generate_documentation_v7.py'),
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    raise FileNotFoundError(
        'Cannot find generate_documentation_v7.py. '
        'Set NEAT_HTML_DOC_SCRIPT env-var or pass script_path= to browse_model().'
    )


def _import_run_generation(script_path):
    parent = str(script_path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    import importlib.util
    spec = importlib.util.spec_from_file_location('_gen_docs_v7', script_path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run_generation


def _fetch_cdm_yaml(neat_session, tmp_dir, verbose=False):
    """Try to export CogniteCore (cdf_cdm) from CDF into a temp YAML.

    Creates a separate NeatSession (same credentials) so the caller's
    loaded data model is not disturbed.  Falls back to bundled YAML on failure.
    """
    try:
        from cognite.neat import NeatSession
        cdm_session = NeatSession(neat_session._client.config)
        sink = contextlib.nullcontext() if verbose else contextlib.redirect_stdout(_io.StringIO())
        with sink:
            cdm_session.physical_data_model.read.cdf('cdf_cdm', 'CogniteCore', 'v1')
        tmp_cdm = Path(tmp_dir) / '_html_doc_cdm_tmp_.yaml'
        with contextlib.redirect_stdout(_io.StringIO()):
            cdm_session.physical_data_model.write.yaml(str(tmp_cdm))
        if tmp_cdm.exists() and tmp_cdm.stat().st_size > 0:
            if verbose:
                print('[html_doc] CogniteCore loaded from CDF')
            return tmp_cdm
    except Exception as exc:
        if verbose:
            print(f'[html_doc] CogniteCore from CDF failed ({exc}); using bundled fallback')
    if _BUNDLED_CDM.exists():
        if verbose:
            print('[html_doc] Using bundled CogniteCore.yaml')
        return _BUNDLED_CDM
    return None


def _fetch_idm_yaml(neat_session, tmp_dir, verbose=False):
    """Try to export CogniteProcessIndustries (cdf_idm) from CDF into a temp YAML.

    Creates a separate NeatSession (same credentials) so the caller's
    loaded data model is not disturbed.  Falls back to bundled YAML on failure.
    """
    try:
        from cognite.neat import NeatSession
        idm_session = NeatSession(neat_session._client.config)
        sink = contextlib.nullcontext() if verbose else contextlib.redirect_stdout(_io.StringIO())
        with sink:
            idm_session.physical_data_model.read.cdf('cdf_idm', 'CogniteProcessIndustries', 'v1')
        tmp_idm = Path(tmp_dir) / '_html_doc_idm_tmp_.yaml'
        with contextlib.redirect_stdout(_io.StringIO()):
            idm_session.physical_data_model.write.yaml(str(tmp_idm))
        if tmp_idm.exists() and tmp_idm.stat().st_size > 0:
            if verbose:
                print('[html_doc] CogniteProcessIndustries loaded from CDF')
            return tmp_idm
    except Exception as exc:
        if verbose:
            print(f'[html_doc] CogniteProcessIndustries from CDF failed ({exc}); using bundled fallback')
    if _BUNDLED_IDM.exists():
        if verbose:
            print('[html_doc] Using bundled CogniteProcessIndustries.yaml')
        return _BUNDLED_IDM
    return None


def html_doc(self, io, cdm=None, idm=None, script_path=None, verbose=False, _neat_session=None):
    """Generate interactive HTML documentation from the loaded NEAT data model.

    Parameters
    ----------
    io : str | Path
        Output path for the generated HTML file.
    cdm : str | Path | None
        Explicit path to a CogniteCore CDM YAML.  When omitted, fetched live
        from CDF (space=cdf_cdm), with the bundled CogniteCore.yaml as fallback.
    idm : str | Path | None
        Explicit path to a CogniteProcessIndustries IDM YAML.  When omitted,
        fetched live from CDF (space=cdf_idm), with the bundled YAML as fallback.
    script_path : str | Path | None
        Explicit path to generate_documentation_v7.py (auto-detected otherwise).
    verbose : bool
        If True, print progress messages.  Defaults to False (quiet).
    """
    output_path = Path(io).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        suffix='.yaml', prefix='_html_doc_tmp_',
        dir=output_path.parent, delete=False,
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)

    cdm_tmp_path = None  # temp CDM file to clean up
    idm_tmp_path = None  # temp IDM file to clean up
    sink = contextlib.nullcontext() if verbose else contextlib.redirect_stdout(_io.StringIO())
    try:
        with sink:
            print(f'[html_doc] Exporting data model to temp YAML: {tmp_path.name}')
            self.yaml(str(tmp_path))
            if not tmp_path.exists() or tmp_path.stat().st_size == 0:
                raise RuntimeError('NEAT yaml export empty. Ensure a data model is loaded.')

            # ── Resolve CDM (CogniteCore / cdf_cdm) ─────────────────────────
            if cdm:
                cdm_path = Path(cdm)
            elif _neat_session is not None:
                fetched = _fetch_cdm_yaml(_neat_session, output_path.parent, verbose=verbose)
                if fetched and fetched != _BUNDLED_CDM:
                    cdm_tmp_path = fetched
                cdm_path = fetched
            else:
                cdm_path = _BUNDLED_CDM if _BUNDLED_CDM.exists() else None

            # ── Resolve IDM (CogniteProcessIndustries / cdf_idm) ────────────
            if idm:
                idm_path = Path(idm)
            elif _neat_session is not None:
                fetched_idm = _fetch_idm_yaml(_neat_session, output_path.parent, verbose=verbose)
                if fetched_idm and fetched_idm != _BUNDLED_IDM:
                    idm_tmp_path = fetched_idm
                idm_path = fetched_idm
            else:
                idm_path = _BUNDLED_IDM if _BUNDLED_IDM.exists() else None

            gen_script = _find_gen_script(script_path)
            print(f'[html_doc] Using: {gen_script}')
            run_gen = _import_run_generation(gen_script)
            result  = run_gen(
                input_path=tmp_path, output_path=output_path,
                cdm_path=cdm_path,
                idm_path=idm_path,
            )
        print(f'[html_doc] Generated: {output_path}' if verbose else f'Generated: {output_path}')
        return result or output_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
        if cdm_tmp_path and cdm_tmp_path.exists():
            cdm_tmp_path.unlink()
        if idm_tmp_path and idm_tmp_path.exists():
            idm_tmp_path.unlink()
