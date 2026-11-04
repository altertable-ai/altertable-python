from importlib.metadata import version, PackageNotFoundError
from .client import Altertable, TrackingMode

try:
    __version__ = version("altertable")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["Altertable", "TrackingMode", "__version__"]
