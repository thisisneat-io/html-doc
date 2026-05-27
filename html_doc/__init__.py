from __future__ import annotations
from types import MethodType
from ._writer import html_doc as _html_doc
from ._exporter import HtmlDocExporter
from .plugin import HtmlDocPlugin

__all__ = ["attach_plugin", "HtmlDocPlugin", "HtmlDocExporter"]


def attach_plugin(neat_session):
    """Monkey-patch html_doc() onto neat.physical_data_model.write.

    This is the session-aware path: CDM and IDM are fetched live from CDF
    using the same credentials as the calling session, before falling back
    to bundled YAML files.

    Usage
    -----
    from html_doc import attach_plugin
    neat = attach_plugin(NeatSession(client))
    neat.physical_data_model.read.cdf("my_space", "my_model", "v1")
    neat.physical_data_model.write.html_doc("docs/model.html")
    """
    write_obj = neat_session.physical_data_model.write

    def _bound(self, io, cdm=None, idm=None, ref_paths=None, env_path=None,
               script_path=None, verbose=False):
        return _html_doc(
            self, io,
            cdm=cdm, idm=idm, ref_paths=ref_paths, env_path=env_path,
            script_path=script_path, verbose=verbose,
            _neat_session=neat_session,
        )

    _bound.__doc__ = _html_doc.__doc__
    write_obj.html_doc = MethodType(_bound, write_obj)
    print("[html_doc] Plugin attached to neat.physical_data_model.write")
    return neat_session
