import importlib
import inspect
import pkgutil
import sys

from .base import AssistantRoute

# --- Auto-discover route classes ---
__all__ = []
route_classes = {}

for _, module_name, _ in pkgutil.iter_modules(__path__):
    if module_name in ("__init__"):
        continue

    module = importlib.import_module(f"{__name__}.{module_name}")
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, AssistantRoute):
            setattr(sys.modules[__name__], name, obj)
            __all__.append(name)
            route_classes[name] = obj

routes_dict = [cls.route() for _, cls in route_classes.items() if cls is not AssistantRoute]
__all__ = list(set(__all__))