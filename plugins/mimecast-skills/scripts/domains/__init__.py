# Mimecast domain modules package

_DOMAIN_REGISTRY: list = []


def register_domain(cls):
    """Decorator that auto-registers a BaseDomain subclass in the domain registry.

    Apply @register_domain to each domain class so it is automatically added to
    DOMAIN_CLASSES without requiring manual list maintenance.
    """
    _DOMAIN_REGISTRY.append(cls)
    return cls


from .awareness_training import AwarenessTrainingDomain
from .directory_sync import DirectorySyncDomain
from .human_risk import HumanRiskDomain

# DOMAIN_CLASSES is populated by @register_domain decorators in each domain module.
DOMAIN_CLASSES = _DOMAIN_REGISTRY
