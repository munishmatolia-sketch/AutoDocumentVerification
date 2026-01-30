"""Service registry for managing microservices architecture components."""

import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """Service status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    """Information about a registered service."""
    name: str
    version: str
    host: str
    port: int
    health_check_url: str
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)


class ServiceRegistry:
    """Registry for managing microservices in the document forensics system."""
    
    def __init__(self):
        """Initialize the service registry."""
        self.services: Dict[str, ServiceInfo] = {}
        self.health_check_interval = 30  # seconds
        self.health_check_timeout = 10  # seconds
        self.health_check_task: Optional[asyncio.Task] = None
        self.running = False
        
        # Service discovery callbacks
        self.service_up_callbacks: List[Callable[[ServiceInfo], None]] = []
        self.service_down_callbacks: List[Callable[[ServiceInfo], None]] = []
    
    def register_service(
        self,
        name: str,
        version: str,
        host: str,
        port: int,
        health_check_url: str,
        metadata: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None
    ) -> None:
        """
        Register a service with the registry.
        
        Args:
            name: Service name
            version: Service version
            host: Service host
            port: Service port
            health_check_url: URL for health checks
            metadata: Additional service metadata
            dependencies: List of service dependencies
        """
        service_info = ServiceInfo(
            name=name,
            version=version,
            host=host,
            port=port,
            health_check_url=health_check_url,
            metadata=metadata or {},
            dependencies=dependencies or []
        )
        
        self.services[name] = service_info
        logger.info(f"Registered service: {name} at {host}:{port}")
    
    def unregister_service(self, name: str) -> bool:
        """
        Unregister a service from the registry.
        
        Args:
            name: Service name to unregister
            
        Returns:
            True if service was unregistered, False if not found
        """
        if name in self.services:
            del self.services[name]
            logger.info(f"Unregistered service: {name}")
            return True
        return False
    
    def get_service(self, name: str) -> Optional[ServiceInfo]:
        """
        Get service information by name.
        
        Args:
            name: Service name
            
        Returns:
            Service information or None if not found
        """
        return self.services.get(name)
    
    def get_healthy_services(self) -> List[ServiceInfo]:
        """
        Get list of all healthy services.
        
        Returns:
            List of healthy services
        """
        return [
            service for service in self.services.values()
            if service.status == ServiceStatus.HEALTHY
        ]
    
    def get_services_by_dependency(self, dependency: str) -> List[ServiceInfo]:
        """
        Get services that depend on a specific service.
        
        Args:
            dependency: Name of the dependency service
            
        Returns:
            List of services that depend on the specified service
        """
        return [
            service for service in self.services.values()
            if dependency in service.dependencies
        ]
    
    async def start_health_monitoring(self) -> None:
        """Start periodic health monitoring of registered services."""
        if self.running:
            logger.warning("Health monitoring is already running")
            return
        
        self.running = True
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("Started health monitoring")
    
    async def stop_health_monitoring(self) -> None:
        """Stop health monitoring."""
        self.running = False
        
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
            self.health_check_task = None
        
        logger.info("Stopped health monitoring")
    
    async def _health_check_loop(self) -> None:
        """Main health check loop."""
        import httpx
        
        while self.running:
            try:
                async with httpx.AsyncClient(timeout=self.health_check_timeout) as client:
                    for service in self.services.values():
                        await self._check_service_health(client, service)
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)  # Short delay before retrying
    
    async def _check_service_health(self, client: 'httpx.AsyncClient', service: ServiceInfo) -> None:
        """
        Check health of a single service.
        
        Args:
            client: HTTP client for making requests
            service: Service to check
        """
        try:
            url = f"http://{service.host}:{service.port}{service.health_check_url}"
            response = await client.get(url)
            
            previous_status = service.status
            
            if response.status_code == 200:
                service.status = ServiceStatus.HEALTHY
                if previous_status != ServiceStatus.HEALTHY:
                    logger.info(f"Service {service.name} is now healthy")
                    self._notify_service_up(service)
            else:
                service.status = ServiceStatus.UNHEALTHY
                if previous_status == ServiceStatus.HEALTHY:
                    logger.warning(f"Service {service.name} is now unhealthy (status: {response.status_code})")
                    self._notify_service_down(service)
            
            service.last_health_check = datetime.utcnow()
            
        except Exception as e:
            previous_status = service.status
            service.status = ServiceStatus.UNHEALTHY
            service.last_health_check = datetime.utcnow()
            
            if previous_status == ServiceStatus.HEALTHY:
                logger.error(f"Service {service.name} health check failed: {e}")
                self._notify_service_down(service)
    
    def _notify_service_up(self, service: ServiceInfo) -> None:
        """Notify callbacks that a service is up."""
        for callback in self.service_up_callbacks:
            try:
                callback(service)
            except Exception as e:
                logger.error(f"Error in service up callback: {e}")
    
    def _notify_service_down(self, service: ServiceInfo) -> None:
        """Notify callbacks that a service is down."""
        for callback in self.service_down_callbacks:
            try:
                callback(service)
            except Exception as e:
                logger.error(f"Error in service down callback: {e}")
    
    def add_service_up_callback(self, callback: Callable[[ServiceInfo], None]) -> None:
        """Add callback for when services come up."""
        self.service_up_callbacks.append(callback)
    
    def add_service_down_callback(self, callback: Callable[[ServiceInfo], None]) -> None:
        """Add callback for when services go down."""
        self.service_down_callbacks.append(callback)
    
    def get_registry_status(self) -> Dict[str, Any]:
        """
        Get overall registry status.
        
        Returns:
            Dictionary with registry status information
        """
        total_services = len(self.services)
        healthy_services = len(self.get_healthy_services())
        unhealthy_services = len([s for s in self.services.values() if s.status == ServiceStatus.UNHEALTHY])
        
        return {
            "total_services": total_services,
            "healthy_services": healthy_services,
            "unhealthy_services": unhealthy_services,
            "monitoring_active": self.running,
            "last_check_interval": self.health_check_interval,
            "services": {
                name: {
                    "status": service.status.value,
                    "last_health_check": service.last_health_check.isoformat() if service.last_health_check else None,
                    "host": service.host,
                    "port": service.port,
                    "version": service.version
                }
                for name, service in self.services.items()
            }
        }
    
    def validate_dependencies(self) -> Dict[str, List[str]]:
        """
        Validate service dependencies and return any missing dependencies.
        
        Returns:
            Dictionary mapping service names to lists of missing dependencies
        """
        missing_deps = {}
        
        for service_name, service in self.services.items():
            missing = []
            for dep in service.dependencies:
                if dep not in self.services:
                    missing.append(dep)
                elif self.services[dep].status != ServiceStatus.HEALTHY:
                    missing.append(f"{dep} (unhealthy)")
            
            if missing:
                missing_deps[service_name] = missing
        
        return missing_deps
    
    async def wait_for_service(self, service_name: str, timeout: int = 60) -> bool:
        """
        Wait for a service to become healthy.
        
        Args:
            service_name: Name of service to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if service became healthy, False if timeout
        """
        start_time = datetime.utcnow()
        timeout_delta = timedelta(seconds=timeout)
        
        while datetime.utcnow() - start_time < timeout_delta:
            service = self.get_service(service_name)
            if service and service.status == ServiceStatus.HEALTHY:
                return True
            
            await asyncio.sleep(1)
        
        return False
    
    async def shutdown_all_services(self) -> None:
        """Gracefully shutdown all registered services."""
        logger.info("Initiating graceful shutdown of all services")
        
        # Stop health monitoring first
        await self.stop_health_monitoring()
        
        # Mark all services as stopping
        for service in self.services.values():
            service.status = ServiceStatus.STOPPING
        
        # Here you would implement actual service shutdown logic
        # For now, we just clear the registry
        self.services.clear()
        logger.info("All services shutdown complete")


# Global service registry instance
service_registry = ServiceRegistry()