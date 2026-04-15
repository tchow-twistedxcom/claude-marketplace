# Mimecast domain modules package

from typing import TypeVar

T = TypeVar('T')

_DOMAIN_REGISTRY: list[type] = []


def register_domain(cls: type[T]) -> type[T]:
    """Decorator that auto-registers a BaseDomain subclass in the domain registry.

    Apply @register_domain to each domain class so it is automatically added to
    DOMAIN_CLASSES without requiring manual list maintenance.
    """
    _DOMAIN_REGISTRY.append(cls)
    return cls


# Deferred imports: domain modules import `register_domain` from this package,
# so they must be imported AFTER the decorator is defined to avoid circular imports.
from .awareness_training import AwarenessTrainingDomain  # noqa: E402
from .directory_sync import DirectorySyncDomain           # noqa: E402
from .human_risk import HumanRiskDomain                   # noqa: E402

# DOMAIN_CLASSES is populated by @register_domain decorators in each domain module.
DOMAIN_CLASSES = _DOMAIN_REGISTRY
