from importlib.metadata import version, PackageNotFoundError
from .client import Altertable

try:
    __version__ = version("altertable")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["Altertable", "__version__"]
