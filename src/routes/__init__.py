import importlib
import inspect
import pkgutil
import sys

from .base import AssistantRoute

# --- Auto-discover route classes ---
__all__ = []
routes_dict = {}

for _, module_name, _ in pkgutil.iter_modules(__path__):
    if module_name in ("__init__"):
        continue

    module = importlib.import_module(f"{__name__}.{module_name}")
    for name, cls in inspect.getmembers(module, inspect.isclass):
        if issubclass(cls, AssistantRoute):
            setattr(sys.modules[__name__], name, cls)
            __all__.append(name)

            if cls is not AssistantRoute:
                routes_dict[name] = cls

routes = [cls for _, cls in routes_dict.items() if cls is not AssistantRoute]
__all__ = list(set(__all__))