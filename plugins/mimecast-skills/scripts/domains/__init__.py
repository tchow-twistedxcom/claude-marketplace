# Mimecast domain modules package

from .awareness_training import AwarenessTrainingDomain
from .human_risk import HumanRiskDomain

DOMAIN_CLASSES = [AwarenessTrainingDomain, HumanRiskDomain]
