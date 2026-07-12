from .connector import AirtableConnector

try:
    from importlib.metadata import version as _version
except ImportError:  # pragma: no cover
    from importlib_metadata import version as _version  # type: ignore

__all__ = ["__version__", "AirtableConnector"]
__version__ = _version("aracnid-core")
