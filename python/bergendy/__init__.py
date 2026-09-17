from .boundary import Boundary, AgentBoundary, BoundaryConfig, BoundaryResult
from .compartments import Compartment, CompartmentConfig

from . import compartments as compartments
from . import hooks as hooks
from . import autopatch as autopatch
from . import graph as graph
from . import audit as audit
from . import maintenance as maintenance
from . import maintenance_agents as maintenance_agents
from . import hunt as hunt
from . import hunt_ports as hunt_ports
from . import redact as redact
from . import pipeline as pipeline
from . import github as github

from importlib.metadata import version as _package_version
try:
    __version__ = _package_version("bergendy")
except Exception:
    try:
        __version__ = _package_version("boundary")
    except Exception:
        __version__ = "1.1.5"


__all__ = [
    "Boundary",
    "AgentBoundary",
    "BoundaryConfig",
    "BoundaryResult",
    "Compartment",
    "CompartmentConfig",
    "compartments",
    "hooks",
    "autopatch",
    "graph",
    "audit",
    "maintenance",
    "maintenance_agents",
    "hunt",
    "hunt_ports",
    "redact",
    "pipeline",
    "github",
]

import sys
import importlib
import importlib.util


class _AliasLoader:
    def __init__(self, target_mod, target_loader=None):
        self.target_mod = target_mod
        self.target_loader = target_loader

    def create_module(self, spec):
        return self.target_mod

    def exec_module(self, module):
        pass

    def get_code(self, fullname):
        if self.target_loader and hasattr(self.target_loader, "get_code"):
            target_name = "bergendy" + fullname[len("boundary"):]
            return self.target_loader.get_code(target_name)
        return None

    def get_source(self, fullname):
        if self.target_loader and hasattr(self.target_loader, "get_source"):
            target_name = "bergendy" + fullname[len("boundary"):]
            return self.target_loader.get_source(target_name)
        return None

    def is_package(self, fullname):
        if self.target_loader and hasattr(self.target_loader, "is_package"):
            target_name = "bergendy" + fullname[len("boundary"):]
            return self.target_loader.is_package(target_name)
        return False

    def get_filename(self, fullname):
        if self.target_loader and hasattr(self.target_loader, "get_filename"):
            target_name = "bergendy" + fullname[len("boundary"):]
            return self.target_loader.get_filename(target_name)
        return getattr(self.target_mod, "__file__", None)


class _BoundaryAliasFinder:
    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        if fullname == "boundary":
            target_name = "bergendy"
        elif fullname.startswith("boundary."):
            target_name = "bergendy." + fullname[len("boundary."):]
        else:
            return None

        target_mod = importlib.import_module(target_name)
        target_spec = getattr(target_mod, "__spec__", None)
        target_loader = getattr(target_spec, "loader", None)
        origin = getattr(target_spec, "origin", None) or getattr(target_mod, "__file__", None)
        return importlib.util.spec_from_loader(
            fullname,
            _AliasLoader(target_mod, target_loader),
            origin=origin,
        )


if not any(getattr(hook, "__name__", "") == "_BoundaryAliasFinder" for hook in sys.meta_path):
    sys.meta_path.insert(0, _BoundaryAliasFinder)


