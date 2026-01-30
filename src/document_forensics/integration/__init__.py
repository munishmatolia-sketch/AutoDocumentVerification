"""Integration module for wiring all document forensics components together."""

from .service_registry import ServiceRegistry
from .health_monitor import HealthMonitor
from .deployment_manager import DeploymentManager

__all__ = ['ServiceRegistry', 'HealthMonitor', 'DeploymentManager']