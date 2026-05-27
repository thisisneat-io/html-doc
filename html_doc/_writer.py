from __future__ import annotations
import contextlib, io as _io, os, sys, tempfile
from pathlib import Path

# ── Bundled paths ────────────────────────────────────────────────────────────
_PKG_DIR = Path(__file__).parent
_BUNDLED_SCRIPT = _PKG_DIR / 'generate_documentation_v9.py'
_BUNDLED_CDM    = _PKG_DIR / 'CogniteCore.yaml'
_BUNDLED_IDM    = _PKG_DIR / 'CogniteProcessIndustries.yaml'


def _find_gen_script(hint=None):
    """Locate generate_documentation_v9.py, preferring bundled copy."""
    candidates = []
    if hint:
        candidates.append(Path(hint))
    env = os.environ.get('NEAT_HTML_DOC_SCRIPT')
    if env:
        candidates.append(Path(env))
    candidates += [
        _BUNDLED_SCRIPT,  # bundled v9 (primary)
        Path(__file__).parent.parent.parent / 'html-doc' / 'html_doc' / 'generate_documentation_v9.py',
        Path(__file__).parent.parent.parent / 'NEAT_PROJECTS' / 'generate_documentation_v9.py',
        Path.cwd() / 'html-doc' / 'html_doc' / 'generate_documentation_v9.py',
        Path.cwd() / 'NEAT_PROJECTS' / 'generate_documentation_v9.py',
        Path.cwd() / 'generate_documentation_v9.py',
        # v8 / v7 fallbacks for backwards compatibility
        _PKG_DIR / 'generate_documentation_v8.py',
        Path(__file__).parent.parent.parent / 'html-doc' / 'html_doc' / 'generate_documentation_v8.py',
        Path(__file__).parent.parent.parent / 'NEAT_PROJECTS' / 'generate_documentation_v8.py',
        Path.cwd() / 'generate_documentation_v8.py',
        Path(__file__).parent.parent.parent / 'NEAT_PROJECTS' / 'generate_documentation_v7.py',
        Path.cwd() / 'generate_documentation_v7.py',
    ]
    for p in candidates:
        if p.exists():
            return p.resolve()
    raise FileNotFoundError(
        'Cannot find generate_documentation_v9.py (or v8/v7 fallback). '
        'Set NEAT_HTML_DOC_SCRIPT env-var or pass script_path= to html_doc().'
    )


def _import_run_generation(script_path):
    parent = str(script_path.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    import importlib.util
    spec = importlib.util.spec_from_file_location('_gen_docs_v9', script_path)
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


def _fetch_ref_yaml(neat_session, space, tmp_dir, verbose=False):
    """Fetch all data models from *space* in CDF into temporary YAML files.

    Creates a separate NeatSession per model so the caller's session is not
    disturbed.  Returns a list of Path objects; caller is responsible for
    clean-up.
    """
    result = []
    try:
        from cognite.neat import NeatSession
        client = neat_session._client
        models = list(client.data_modeling.data_models.list(space=space, limit=25))
        if not models:
            if verbose:
                print(f'[html_doc] No data models found in CDF space "{space}"')
            return result
        for m in models:
            try:
                tmp_yaml = Path(tmp_dir) / f'_html_doc_ref_{space}_{m.external_id}_{m.version}_.yaml'
                ref_session = NeatSession(client.config)
                sink = contextlib.nullcontext() if verbose else contextlib.redirect_stdout(_io.StringIO())
                with sink:
                    ref_session.physical_data_model.read.cdf(space, m.external_id, m.version)
                    ref_session.physical_data_model.write.yaml(str(tmp_yaml))
                if tmp_yaml.exists() and tmp_yaml.stat().st_size > 0:
                    if verbose:
                        print(f'[html_doc] Ref model {space}:{m.external_id} v{m.version} loaded from CDF')
                    result.append(tmp_yaml)
            except Exception as exc:
                if verbose:
                    print(f'[html_doc] Could not fetch {space}:{getattr(m, "external_id", "?")}: {exc}')
    except Exception as exc:
        if verbose:
            print(f'[html_doc] Ref fetch failed for space "{space}": {exc}')
    return result


def html_doc(self, io, cdm=None, idm=None, ref_paths=None, env_path=None,
             script_path=None, verbose=False, _neat_session=None):
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
    ref_paths : list[str | Path] | None
        Explicit YAML paths for additional reference models declared in the
        model's ``governedSpaces`` metadata field.  Auto-discovery and CDF
        fetching are used for spaces not covered by these paths.
    env_path : str | Path | None
        Path to a .env file with CDF credentials used to fetch reference
        models for governed spaces that cannot be resolved from local files.
        Only used in the standalone (non-session) path; when *_neat_session*
        is supplied, the live session is used instead.
    script_path : str | Path | None
        Explicit path to generate_documentation_v9.py (auto-detected otherwise).
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

    cdm_tmp_path = None   # temp CDM file to clean up
    idm_tmp_path = None   # temp IDM file to clean up
    ref_tmp_paths = []    # temp ref YAML files to clean up
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

            # ── Resolve ref models from governedSpaces (via session or env) ─
            # The generation script handles auto-discovery and YAML loading;
            # here we only pre-fetch spaces from CDF when a live session is
            # available (no env_path needed in that case).
            resolved_ref_paths = list(ref_paths or [])
            if _neat_session is not None:
                import tempfile as _tmpmod, yaml as _yaml
                _ref_tmp_dir = Path(_tmpmod.mkdtemp(prefix='_html_doc_ref_'))
                try:
                    # Peek at the exported YAML to find governedSpaces
                    with open(tmp_path, encoding='utf-8', errors='replace') as _f:
                        _raw = _yaml.safe_load(_f) or {}
                    _meta = _raw.get('metadata', _raw.get('Metadata', {})) or {}
                    _governed_raw = _meta.get('governedSpaces', '')
                    _system = {'cdf_cdm', 'cdf_idm'}
                    _model_space = _meta.get('space', '')
                    _ref_spaces = [
                        s.strip()
                        for s in str(_governed_raw).replace(';', ',').split(',')
                        if s.strip() and s.strip() not in _system and s.strip() != _model_space
                    ]
                    # Build set of spaces already covered by explicit ref_paths
                    _covered = set()
                    for _rp in resolved_ref_paths:
                        _rp = Path(_rp)
                        if _rp.exists():
                            try:
                                with open(_rp, encoding='utf-8') as _rf:
                                    _rm = _yaml.safe_load(_rf) or {}
                                _rs = (_rm.get('metadata') or _rm.get('Metadata') or {}).get('space', '')
                                if _rs:
                                    _covered.add(_rs)
                            except Exception:
                                pass
                    for _rs in _ref_spaces:
                        if _rs in _covered:
                            continue
                        _fetched = _fetch_ref_yaml(_neat_session, _rs, _ref_tmp_dir, verbose=verbose)
                        ref_tmp_paths.extend(_fetched)
                        resolved_ref_paths.extend(str(p) for p in _fetched)
                except Exception as _exc:
                    if verbose:
                        print(f'[html_doc] governedSpaces pre-fetch warning: {_exc}')

            gen_script = _find_gen_script(script_path)
            print(f'[html_doc] Using: {gen_script}')
            run_gen = _import_run_generation(gen_script)
            result  = run_gen(
                input_path=tmp_path,
                output_path=output_path,
                cdm_path=cdm_path,
                idm_path=idm_path,
                ref_paths=resolved_ref_paths or None,
                env_path=env_path,
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
        for _rtp in ref_tmp_paths:
            try:
                Path(_rtp).unlink()
            except Exception:
                pass
