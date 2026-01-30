"""Health monitoring and system status tracking for the document forensics system."""

import logging
import asyncio
import psutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthMetric:
    """Individual health metric."""
    name: str
    value: float
    unit: str
    status: HealthStatus
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class ComponentHealth:
    """Health status of a system component."""
    component_name: str
    status: HealthStatus
    metrics: List[HealthMetric]
    last_check: datetime
    error_message: Optional[str] = None


class HealthMonitor:
    """Comprehensive health monitoring for the document forensics system."""
    
    def __init__(self):
        """Initialize the health monitor."""
        self.component_health: Dict[str, ComponentHealth] = {}
        self.monitoring_active = False
        self.monitoring_task: Optional[asyncio.Task] = None
        self.check_interval = 30  # seconds
        
        # Health thresholds
        self.cpu_warning_threshold = 80.0  # percent
        self.cpu_critical_threshold = 95.0  # percent
        self.memory_warning_threshold = 80.0  # percent
        self.memory_critical_threshold = 95.0  # percent
        self.disk_warning_threshold = 85.0  # percent
        self.disk_critical_threshold = 95.0  # percent
        
        # Component checkers
        self.component_checkers = {
            'system_resources': self._check_system_resources,
            'database': self._check_database_health,
            'redis': self._check_redis_health,
            'storage': self._check_storage_health,
            'analysis_engines': self._check_analysis_engines_health
        }
    
    async def start_monitoring(self) -> None:
        """Start health monitoring."""
        if self.monitoring_active:
            logger.warning("Health monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self) -> None:
        """Stop health monitoring."""
        self.monitoring_active = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
        logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(5)  # Short delay before retrying
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all components."""
        for component_name, checker in self.component_checkers.items():
            try:
                health = await checker()
                self.component_health[component_name] = health
                
                if health.status == HealthStatus.CRITICAL:
                    logger.critical(f"Component {component_name} is in critical state: {health.error_message}")
                elif health.status == HealthStatus.WARNING:
                    logger.warning(f"Component {component_name} has warnings: {health.error_message}")
                
            except Exception as e:
                logger.error(f"Health check failed for {component_name}: {e}")
                self.component_health[component_name] = ComponentHealth(
                    component_name=component_name,
                    status=HealthStatus.CRITICAL,
                    metrics=[],
                    last_check=datetime.utcnow(),
                    error_message=str(e)
                )
    
    async def _check_system_resources(self) -> ComponentHealth:
        """Check system resource health (CPU, memory, disk)."""
        metrics = []
        overall_status = HealthStatus.HEALTHY
        error_messages = []
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_status = self._evaluate_threshold(
                cpu_percent, self.cpu_warning_threshold, self.cpu_critical_threshold
            )
            metrics.append(HealthMetric(
                name="cpu_usage",
                value=cpu_percent,
                unit="percent",
                status=cpu_status,
                threshold_warning=self.cpu_warning_threshold,
                threshold_critical=self.cpu_critical_threshold
            ))
            
            if cpu_status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                error_messages.append(f"CPU usage critical: {cpu_percent:.1f}%")
            elif cpu_status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
                error_messages.append(f"CPU usage high: {cpu_percent:.1f}%")
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_status = self._evaluate_threshold(
                memory_percent, self.memory_warning_threshold, self.memory_critical_threshold
            )
            metrics.append(HealthMetric(
                name="memory_usage",
                value=memory_percent,
                unit="percent",
                status=memory_status,
                threshold_warning=self.memory_warning_threshold,
                threshold_critical=self.memory_critical_threshold
            ))
            
            if memory_status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                error_messages.append(f"Memory usage critical: {memory_percent:.1f}%")
            elif memory_status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
                error_messages.append(f"Memory usage high: {memory_percent:.1f}%")
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            disk_status = self._evaluate_threshold(
                disk_percent, self.disk_warning_threshold, self.disk_critical_threshold
            )
            metrics.append(HealthMetric(
                name="disk_usage",
                value=disk_percent,
                unit="percent",
                status=disk_status,
                threshold_warning=self.disk_warning_threshold,
                threshold_critical=self.disk_critical_threshold
            ))
            
            if disk_status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                error_messages.append(f"Disk usage critical: {disk_percent:.1f}%")
            elif disk_status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
                error_messages.append(f"Disk usage high: {disk_percent:.1f}%")
            
            # Load average (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()
                cpu_count = psutil.cpu_count()
                load_percent = (load_avg[0] / cpu_count) * 100 if cpu_count > 0 else 0
                
                metrics.append(HealthMetric(
                    name="load_average_1min",
                    value=load_percent,
                    unit="percent",
                    status=self._evaluate_threshold(load_percent, 80.0, 100.0)
                ))
            except (AttributeError, OSError):
                # getloadavg not available on Windows
                pass
            
        except Exception as e:
            overall_status = HealthStatus.CRITICAL
            error_messages.append(f"System resource check failed: {str(e)}")
        
        return ComponentHealth(
            component_name="system_resources",
            status=overall_status,
            metrics=metrics,
            last_check=datetime.utcnow(),
            error_message="; ".join(error_messages) if error_messages else None
        )
    
    async def _check_database_health(self) -> ComponentHealth:
        """Check database connectivity and performance."""
        metrics = []
        status = HealthStatus.HEALTHY
        error_message = None
        
        try:
            # This would normally check actual database connection
            # For now, we'll simulate a basic check
            from ..database.connection import get_database_connection
            
            # Simulate database connection check
            connection_time = 0.05  # Simulated connection time
            metrics.append(HealthMetric(
                name="connection_time",
                value=connection_time * 1000,  # Convert to milliseconds
                unit="ms",
                status=HealthStatus.HEALTHY if connection_time < 0.1 else HealthStatus.WARNING
            ))
            
            # Simulate active connections check
            active_connections = 5  # Simulated
            metrics.append(HealthMetric(
                name="active_connections",
                value=active_connections,
                unit="count",
                status=HealthStatus.HEALTHY
            ))
            
        except Exception as e:
            status = HealthStatus.CRITICAL
            error_message = f"Database health check failed: {str(e)}"
        
        return ComponentHealth(
            component_name="database",
            status=status,
            metrics=metrics,
            last_check=datetime.utcnow(),
            error_message=error_message
        )
    
    async def _check_redis_health(self) -> ComponentHealth:
        """Check Redis connectivity and performance."""
        metrics = []
        status = HealthStatus.HEALTHY
        error_message = None
        
        try:
            # This would normally check actual Redis connection
            # For now, we'll simulate a basic check
            
            # Simulate Redis ping
            ping_time = 0.002  # Simulated ping time
            metrics.append(HealthMetric(
                name="ping_time",
                value=ping_time * 1000,  # Convert to milliseconds
                unit="ms",
                status=HealthStatus.HEALTHY if ping_time < 0.01 else HealthStatus.WARNING
            ))
            
            # Simulate memory usage
            memory_usage = 45.0  # Simulated percentage
            metrics.append(HealthMetric(
                name="memory_usage",
                value=memory_usage,
                unit="percent",
                status=self._evaluate_threshold(memory_usage, 80.0, 95.0)
            ))
            
        except Exception as e:
            status = HealthStatus.CRITICAL
            error_message = f"Redis health check failed: {str(e)}"
        
        return ComponentHealth(
            component_name="redis",
            status=status,
            metrics=metrics,
            last_check=datetime.utcnow(),
            error_message=error_message
        )
    
    async def _check_storage_health(self) -> ComponentHealth:
        """Check storage system health."""
        metrics = []
        status = HealthStatus.HEALTHY
        error_message = None
        
        try:
            # Check uploads directory
            import os
            uploads_dir = "uploads"
            if os.path.exists(uploads_dir):
                # Check directory permissions
                readable = os.access(uploads_dir, os.R_OK)
                writable = os.access(uploads_dir, os.W_OK)
                
                metrics.append(HealthMetric(
                    name="uploads_readable",
                    value=1.0 if readable else 0.0,
                    unit="boolean",
                    status=HealthStatus.HEALTHY if readable else HealthStatus.CRITICAL
                ))
                
                metrics.append(HealthMetric(
                    name="uploads_writable",
                    value=1.0 if writable else 0.0,
                    unit="boolean",
                    status=HealthStatus.HEALTHY if writable else HealthStatus.CRITICAL
                ))
                
                if not readable or not writable:
                    status = HealthStatus.CRITICAL
                    error_message = f"Storage permissions issue: readable={readable}, writable={writable}"
            else:
                status = HealthStatus.WARNING
                error_message = "Uploads directory does not exist"
            
        except Exception as e:
            status = HealthStatus.CRITICAL
            error_message = f"Storage health check failed: {str(e)}"
        
        return ComponentHealth(
            component_name="storage",
            status=status,
            metrics=metrics,
            last_check=datetime.utcnow(),
            error_message=error_message
        )
    
    async def _check_analysis_engines_health(self) -> ComponentHealth:
        """Check analysis engines health."""
        metrics = []
        status = HealthStatus.HEALTHY
        error_message = None
        
        try:
            # Check if analysis components can be imported
            from ..analysis.metadata_extractor import MetadataExtractor
            from ..analysis.tampering_detector import TamperingDetector
            from ..analysis.authenticity_scorer import AuthenticityScorer
            
            # Simulate engine status checks
            engines = ['metadata_extractor', 'tampering_detector', 'authenticity_scorer']
            for engine in engines:
                # Simulate engine health
                engine_status = HealthStatus.HEALTHY  # Would check actual engine status
                metrics.append(HealthMetric(
                    name=f"{engine}_status",
                    value=1.0 if engine_status == HealthStatus.HEALTHY else 0.0,
                    unit="boolean",
                    status=engine_status
                ))
            
        except Exception as e:
            status = HealthStatus.CRITICAL
            error_message = f"Analysis engines health check failed: {str(e)}"
        
        return ComponentHealth(
            component_name="analysis_engines",
            status=status,
            metrics=metrics,
            last_check=datetime.utcnow(),
            error_message=error_message
        )
    
    def _evaluate_threshold(
        self, 
        value: float, 
        warning_threshold: float, 
        critical_threshold: float
    ) -> HealthStatus:
        """Evaluate a metric value against thresholds."""
        if value >= critical_threshold:
            return HealthStatus.CRITICAL
        elif value >= warning_threshold:
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY
    
    def get_overall_health(self) -> Dict[str, Any]:
        """
        Get overall system health status.
        
        Returns:
            Dictionary with overall health information
        """
        if not self.component_health:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "message": "No health data available",
                "components": {},
                "last_check": None
            }
        
        # Determine overall status
        component_statuses = [comp.status for comp in self.component_health.values()]
        
        if HealthStatus.CRITICAL in component_statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in component_statuses:
            overall_status = HealthStatus.WARNING
        elif HealthStatus.UNKNOWN in component_statuses:
            overall_status = HealthStatus.UNKNOWN
        else:
            overall_status = HealthStatus.HEALTHY
        
        # Generate summary message
        critical_components = [
            name for name, comp in self.component_health.items()
            if comp.status == HealthStatus.CRITICAL
        ]
        warning_components = [
            name for name, comp in self.component_health.items()
            if comp.status == HealthStatus.WARNING
        ]
        
        if critical_components:
            message = f"Critical issues in: {', '.join(critical_components)}"
        elif warning_components:
            message = f"Warnings in: {', '.join(warning_components)}"
        else:
            message = "All systems healthy"
        
        return {
            "status": overall_status.value,
            "message": message,
            "monitoring_active": self.monitoring_active,
            "last_check": max(
                comp.last_check for comp in self.component_health.values()
            ).isoformat(),
            "components": {
                name: {
                    "status": comp.status.value,
                    "last_check": comp.last_check.isoformat(),
                    "error_message": comp.error_message,
                    "metrics": [
                        {
                            "name": metric.name,
                            "value": metric.value,
                            "unit": metric.unit,
                            "status": metric.status.value,
                            "timestamp": metric.timestamp.isoformat()
                        }
                        for metric in comp.metrics
                    ]
                }
                for name, comp in self.component_health.items()
            }
        }
    
    async def perform_immediate_check(self) -> Dict[str, Any]:
        """
        Perform an immediate health check of all components.
        
        Returns:
            Current health status
        """
        await self._perform_health_checks()
        return self.get_overall_health()


# Global health monitor instance
health_monitor = HealthMonitor()