from __future__ import annotations
from typing import ClassVar, Any

from cognite.neat._plugin_adapter import PhysicalDataModelFileWriterPlugin

from ._exporter import HtmlDocExporter


class HtmlDocPlugin(PhysicalDataModelFileWriterPlugin):
    """NEAT plugin that generates interactive HTML documentation from a data model."""

    _entry_point: ClassVar[str] = "cognite.neat.plugin.data_model.file_writers"
    method_name: ClassVar[str] = "html_doc"

    def configure(self, **kwargs: Any) -> HtmlDocExporter:
        """Return a configured HtmlDocExporter.

        All keyword arguments are forwarded to HtmlDocExporter.__init__:
        io, cdm, idm, script_path, verbose, neat_session.
        """
        return HtmlDocExporter(**kwargs)
