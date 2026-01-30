"""
System integrator that wires all components together for the document forensics system.

This module provides the main integration point for starting up the complete system
with all components properly connected and configured.
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any, Optional
from pathlib import Path

from .service_registry import service_registry, ServiceRegistry
from .health_monitor import health_monitor, HealthMonitor
from .deployment_manager import deployment_manager, DeploymentManager
from ..workflow.workflow_manager import WorkflowManager
from ..api.main import create_app
from ..core.config import settings

logger = logging.getLogger(__name__)


class SystemIntegrator:
    """Main system integrator for the document forensics system."""
    
    def __init__(self):
        """Initialize the system integrator."""
        self.service_registry = service_registry
        self.health_monitor = health_monitor
        self.deployment_manager = deployment_manager
        self.workflow_manager = WorkflowManager()
        
        self.running = False
        self.shutdown_event = asyncio.Event()
        
        # Component status
        self.components_started = {
            'service_registry': False,
            'health_monitor': False,
            'workflow_manager': False,
            'api_server': False
        }
    
    async def initialize_system(self) -> bool:
        """
        Initialize the complete document forensics system.
        
        Returns:
            True if initialization successful
        """
        try:
            logger.info("Initializing Document Forensics System...")
            
            # Register core services
            await self._register_core_services()
            
            # Start service registry monitoring
            await self.service_registry.start_health_monitoring()
            self.components_started['service_registry'] = True
            logger.info("Service registry started")
            
            # Start health monitoring
            await self.health_monitor.start_monitoring()
            self.components_started['health_monitor'] = True
            logger.info("Health monitoring started")
            
            # Initialize workflow manager
            # The workflow manager is already initialized, just mark as started
            self.components_started['workflow_manager'] = True
            logger.info("Workflow manager initialized")
            
            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            logger.info("System initialization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"System initialization failed: {str(e)}")
            await self._cleanup_components()
            return False
    
    async def _register_core_services(self) -> None:
        """Register core services with the service registry."""
        
        # Register API service
        self.service_registry.register_service(
            name="api",
            version="1.0.0",
            host="localhost",
            port=8000,
            health_check_url="/health",
            metadata={
                "type": "api",
                "public": True,
                "description": "Main API service for document forensics"
            },
            dependencies=["postgres", "redis"]
        )
        
        # Register database service
        self.service_registry.register_service(
            name="postgres",
            version="15",
            host="localhost",
            port=5432,
            health_check_url="/health",
            metadata={
                "type": "database",
                "persistent": True,
                "description": "PostgreSQL database"
            }
        )
        
        # Register Redis service
        self.service_registry.register_service(
            name="redis",
            version="7",
            host="localhost",
            port=6379,
            health_check_url="/health",
            metadata={
                "type": "cache",
                "persistent": False,
                "description": "Redis cache and message broker"
            }
        )
        
        # Register worker service
        self.service_registry.register_service(
            name="worker",
            version="1.0.0",
            host="localhost",
            port=8001,
            health_check_url="/health",
            metadata={
                "type": "worker",
                "public": False,
                "description": "Celery worker for background processing"
            },
            dependencies=["postgres", "redis"]
        )
        
        # Register web interface
        self.service_registry.register_service(
            name="web",
            version="1.0.0",
            host="localhost",
            port=8501,
            health_check_url="/",
            metadata={
                "type": "frontend",
                "public": True,
                "description": "Streamlit web interface"
            },
            dependencies=["api"]
        )
        
        logger.info("Core services registered with service registry")
    
    def _setup_signal_handlers(self) -> None:
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start_api_server(self, host: str = "0.0.0.0", port: int = 8000) -> bool:
        """
        Start the API server.
        
        Args:
            host: Host to bind to
            port: Port to bind to
            
        Returns:
            True if server started successfully
        """
        try:
            import uvicorn
            
            # Create FastAPI app
            app = create_app()
            
            # Configure uvicorn
            config = uvicorn.Config(
                app=app,
                host=host,
                port=port,
                log_level=settings.log_level.lower(),
                access_log=True
            )
            
            server = uvicorn.Server(config)
            
            # Start server in background task
            server_task = asyncio.create_task(server.serve())
            
            # Wait a moment for server to start
            await asyncio.sleep(2)
            
            self.components_started['api_server'] = True
            logger.info(f"API server started on {host}:{port}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start API server: {str(e)}")
            return False
    
    async def run_system(self, start_api: bool = True) -> None:
        """
        Run the complete document forensics system.
        
        Args:
            start_api: Whether to start the API server
        """
        try:
            # Initialize system
            if not await self.initialize_system():
                logger.error("System initialization failed")
                return
            
            # Start API server if requested
            if start_api:
                if not await self.start_api_server():
                    logger.error("Failed to start API server")
                    await self.shutdown()
                    return
            
            self.running = True
            logger.info("Document Forensics System is running")
            
            # Display system status
            await self._display_system_status()
            
            # Wait for shutdown signal
            await self.shutdown_event.wait()
            
        except Exception as e:
            logger.error(f"System runtime error: {str(e)}")
        finally:
            await self.shutdown()
    
    async def _display_system_status(self) -> None:
        """Display current system status."""
        logger.info("=== System Status ===")
        
        # Service registry status
        registry_status = self.service_registry.get_registry_status()
        logger.info(f"Services: {registry_status['healthy_services']}/{registry_status['total_services']} healthy")
        
        # Health monitor status
        health_status = await self.health_monitor.perform_immediate_check()
        logger.info(f"Overall Health: {health_status['status']}")
        
        # Workflow manager status
        workflow_status = self.workflow_manager.get_system_status()
        logger.info(f"Active Batches: {workflow_status['active_batches']}")
        logger.info(f"Active Documents: {workflow_status['active_documents']}")
        
        # Component status
        logger.info("Components:")
        for component, started in self.components_started.items():
            status = "✓" if started else "✗"
            logger.info(f"  {status} {component}")
        
        logger.info("=====================")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the system."""
        if not self.running:
            return
        
        logger.info("Shutting down Document Forensics System...")
        self.running = False
        
        await self._cleanup_components()
        
        # Set shutdown event
        self.shutdown_event.set()
        
        logger.info("System shutdown completed")
    
    async def _cleanup_components(self) -> None:
        """Clean up all system components."""
        
        # Stop health monitoring
        if self.components_started.get('health_monitor'):
            try:
                await self.health_monitor.stop_monitoring()
                self.components_started['health_monitor'] = False
                logger.info("Health monitoring stopped")
            except Exception as e:
                logger.error(f"Error stopping health monitor: {str(e)}")
        
        # Stop service registry monitoring
        if self.components_started.get('service_registry'):
            try:
                await self.service_registry.stop_health_monitoring()
                self.components_started['service_registry'] = False
                logger.info("Service registry monitoring stopped")
            except Exception as e:
                logger.error(f"Error stopping service registry: {str(e)}")
        
        # Clean up workflow manager
        if self.components_started.get('workflow_manager'):
            try:
                self.workflow_manager.cleanup_completed_batches(max_age_hours=0)
                self.components_started['workflow_manager'] = False
                logger.info("Workflow manager cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up workflow manager: {str(e)}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get comprehensive system information.
        
        Returns:
            Dictionary with system information
        """
        return {
            'running': self.running,
            'components': self.components_started.copy(),
            'service_registry': self.service_registry.get_registry_status(),
            'workflow_manager': self.workflow_manager.get_system_status(),
            'settings': {
                'log_level': settings.log_level,
                'max_file_size': settings.max_file_size,
                'allowed_file_types': settings.allowed_file_types
            }
        }


# Global system integrator instance
system_integrator = SystemIntegrator()


async def main():
    """Main entry point for running the complete system."""
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the system
    await system_integrator.run_system()


if __name__ == "__main__":
    asyncio.run(main())