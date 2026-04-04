# Mimecast domain modules package

from .awareness_training import AwarenessTrainingDomain
from .directory_sync import DirectorySyncDomain
from .human_risk import HumanRiskDomain

DOMAIN_CLASSES = [AwarenessTrainingDomain, DirectorySyncDomain, HumanRiskDomain]
