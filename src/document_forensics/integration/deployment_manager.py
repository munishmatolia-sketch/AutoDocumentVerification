"""Deployment management and orchestration for the document forensics system."""

import logging
import asyncio
import yaml
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from .service_registry import ServiceRegistry, service_registry
from .health_monitor import HealthMonitor, health_monitor

logger = logging.getLogger(__name__)


class DeploymentStatus(Enum):
    """Deployment status enumeration."""
    PENDING = "pending"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class DeploymentConfig:
    """Configuration for a deployment."""
    name: str
    version: str
    services: List[Dict[str, Any]]
    environment: str
    replicas: int = 1
    resources: Optional[Dict[str, Any]] = None
    health_checks: Optional[Dict[str, Any]] = None


class DeploymentManager:
    """Manages deployment and orchestration of the document forensics system."""
    
    def __init__(self, service_registry: ServiceRegistry, health_monitor: HealthMonitor):
        """
        Initialize the deployment manager.
        
        Args:
            service_registry: Service registry instance
            health_monitor: Health monitor instance
        """
        self.service_registry = service_registry
        self.health_monitor = health_monitor
        self.deployments: Dict[str, Dict[str, Any]] = {}
        self.deployment_configs: Dict[str, DeploymentConfig] = {}
    
    def load_deployment_config(self, config_path: str) -> DeploymentConfig:
        """
        Load deployment configuration from file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Deployment configuration
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Deployment config not found: {config_path}")
        
        with open(config_file, 'r') as f:
            if config_file.suffix.lower() in ['.yml', '.yaml']:
                config_data = yaml.safe_load(f)
            else:
                config_data = json.load(f)
        
        deployment_config = DeploymentConfig(
            name=config_data['name'],
            version=config_data['version'],
            services=config_data['services'],
            environment=config_data.get('environment', 'development'),
            replicas=config_data.get('replicas', 1),
            resources=config_data.get('resources'),
            health_checks=config_data.get('health_checks')
        )
        
        self.deployment_configs[deployment_config.name] = deployment_config
        logger.info(f"Loaded deployment config: {deployment_config.name}")
        
        return deployment_config
    
    async def deploy(self, deployment_name: str, config: Optional[DeploymentConfig] = None) -> bool:
        """
        Deploy the system using the specified configuration.
        
        Args:
            deployment_name: Name of the deployment
            config: Optional deployment configuration (uses loaded config if not provided)
            
        Returns:
            True if deployment successful, False otherwise
        """
        if config is None:
            config = self.deployment_configs.get(deployment_name)
            if config is None:
                logger.error(f"No configuration found for deployment: {deployment_name}")
                return False
        
        logger.info(f"Starting deployment: {deployment_name}")
        
        # Initialize deployment status
        self.deployments[deployment_name] = {
            'status': DeploymentStatus.DEPLOYING,
            'config': config,
            'start_time': datetime.utcnow(),
            'services': {},
            'errors': []
        }
        
        try:
            # Deploy services in dependency order
            service_order = self._calculate_deployment_order(config.services)
            
            for service_config in service_order:
                success = await self._deploy_service(deployment_name, service_config)
                if not success:
                    await self._rollback_deployment(deployment_name)
                    return False
            
            # Start health monitoring
            await self.health_monitor.start_monitoring()
            await self.service_registry.start_health_monitoring()
            
            # Wait for all services to be healthy
            all_healthy = await self._wait_for_healthy_deployment(deployment_name, timeout=300)
            
            if all_healthy:
                self.deployments[deployment_name]['status'] = DeploymentStatus.DEPLOYED
                self.deployments[deployment_name]['deployed_time'] = datetime.utcnow()
                logger.info(f"Deployment successful: {deployment_name}")
                return True
            else:
                logger.error(f"Deployment health check failed: {deployment_name}")
                await self._rollback_deployment(deployment_name)
                return False
                
        except Exception as e:
            logger.error(f"Deployment failed: {deployment_name} - {str(e)}")
            self.deployments[deployment_name]['status'] = DeploymentStatus.FAILED
            self.deployments[deployment_name]['errors'].append(str(e))
            await self._rollback_deployment(deployment_name)
            return False
    
    async def _deploy_service(self, deployment_name: str, service_config: Dict[str, Any]) -> bool:
        """
        Deploy a single service.
        
        Args:
            deployment_name: Name of the deployment
            service_config: Service configuration
            
        Returns:
            True if service deployed successfully
        """
        service_name = service_config['name']
        logger.info(f"Deploying service: {service_name}")
        
        try:
            # Register service with service registry
            self.service_registry.register_service(
                name=service_name,
                version=service_config.get('version', '1.0.0'),
                host=service_config.get('host', 'localhost'),
                port=service_config.get('port', 8000),
                health_check_url=service_config.get('health_check_url', '/health'),
                metadata=service_config.get('metadata', {}),
                dependencies=service_config.get('dependencies', [])
            )
            
            # Update deployment status
            self.deployments[deployment_name]['services'][service_name] = {
                'status': 'deployed',
                'config': service_config,
                'deployed_time': datetime.utcnow()
            }
            
            logger.info(f"Service deployed successfully: {service_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to deploy service {service_name}: {str(e)}")
            self.deployments[deployment_name]['errors'].append(f"Service {service_name}: {str(e)}")
            return False
    
    def _calculate_deployment_order(self, services: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Calculate the order in which services should be deployed based on dependencies.
        
        Args:
            services: List of service configurations
            
        Returns:
            Services ordered by dependencies
        """
        # Simple topological sort based on dependencies
        service_map = {svc['name']: svc for svc in services}
        deployed = set()
        ordered_services = []
        
        def can_deploy(service):
            dependencies = service.get('dependencies', [])
            return all(dep in deployed for dep in dependencies)
        
        while len(ordered_services) < len(services):
            deployable = [
                svc for svc in services 
                if svc['name'] not in deployed and can_deploy(svc)
            ]
            
            if not deployable:
                # Handle circular dependencies or missing dependencies
                remaining = [svc for svc in services if svc['name'] not in deployed]
                logger.warning(f"Circular or missing dependencies detected, deploying remaining services: {[s['name'] for s in remaining]}")
                deployable = remaining
            
            for service in deployable:
                ordered_services.append(service)
                deployed.add(service['name'])
        
        return ordered_services
    
    async def _wait_for_healthy_deployment(self, deployment_name: str, timeout: int = 300) -> bool:
        """
        Wait for all services in a deployment to become healthy.
        
        Args:
            deployment_name: Name of the deployment
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all services are healthy
        """
        start_time = datetime.utcnow()
        
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            deployment = self.deployments.get(deployment_name)
            if not deployment:
                return False
            
            service_names = list(deployment['services'].keys())
            healthy_services = []
            
            for service_name in service_names:
                if await self.service_registry.wait_for_service(service_name, timeout=5):
                    healthy_services.append(service_name)
            
            if len(healthy_services) == len(service_names):
                logger.info(f"All services healthy for deployment: {deployment_name}")
                return True
            
            logger.info(f"Waiting for services to become healthy: {len(healthy_services)}/{len(service_names)}")
            await asyncio.sleep(10)
        
        logger.error(f"Timeout waiting for healthy deployment: {deployment_name}")
        return False
    
    async def _rollback_deployment(self, deployment_name: str) -> None:
        """
        Rollback a failed deployment.
        
        Args:
            deployment_name: Name of the deployment to rollback
        """
        logger.info(f"Rolling back deployment: {deployment_name}")
        
        deployment = self.deployments.get(deployment_name)
        if not deployment:
            return
        
        # Stop all services in reverse order
        service_names = list(deployment['services'].keys())
        for service_name in reversed(service_names):
            try:
                self.service_registry.unregister_service(service_name)
                logger.info(f"Unregistered service during rollback: {service_name}")
            except Exception as e:
                logger.error(f"Error during rollback of service {service_name}: {str(e)}")
        
        deployment['status'] = DeploymentStatus.FAILED
        deployment['rollback_time'] = datetime.utcnow()
    
    async def stop_deployment(self, deployment_name: str) -> bool:
        """
        Stop a running deployment.
        
        Args:
            deployment_name: Name of the deployment to stop
            
        Returns:
            True if stopped successfully
        """
        deployment = self.deployments.get(deployment_name)
        if not deployment:
            logger.error(f"Deployment not found: {deployment_name}")
            return False
        
        logger.info(f"Stopping deployment: {deployment_name}")
        deployment['status'] = DeploymentStatus.STOPPING
        
        try:
            # Stop health monitoring
            await self.health_monitor.stop_monitoring()
            await self.service_registry.stop_health_monitoring()
            
            # Stop all services
            service_names = list(deployment['services'].keys())
            for service_name in reversed(service_names):
                self.service_registry.unregister_service(service_name)
                deployment['services'][service_name]['status'] = 'stopped'
            
            deployment['status'] = DeploymentStatus.STOPPED
            deployment['stopped_time'] = datetime.utcnow()
            
            logger.info(f"Deployment stopped successfully: {deployment_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping deployment {deployment_name}: {str(e)}")
            deployment['status'] = DeploymentStatus.FAILED
            deployment['errors'].append(f"Stop error: {str(e)}")
            return False
    
    def get_deployment_status(self, deployment_name: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a deployment.
        
        Args:
            deployment_name: Name of the deployment
            
        Returns:
            Deployment status information
        """
        deployment = self.deployments.get(deployment_name)
        if not deployment:
            return None
        
        # Get service health information
        service_health = {}
        for service_name in deployment['services'].keys():
            service_info = self.service_registry.get_service(service_name)
            if service_info:
                service_health[service_name] = {
                    'status': service_info.status.value,
                    'last_health_check': service_info.last_health_check.isoformat() if service_info.last_health_check else None
                }
        
        return {
            'name': deployment_name,
            'status': deployment['status'].value,
            'start_time': deployment['start_time'].isoformat(),
            'deployed_time': deployment.get('deployed_time', {}).isoformat() if deployment.get('deployed_time') else None,
            'services': deployment['services'],
            'service_health': service_health,
            'errors': deployment['errors'],
            'config': {
                'name': deployment['config'].name,
                'version': deployment['config'].version,
                'environment': deployment['config'].environment,
                'replicas': deployment['config'].replicas
            }
        }
    
    def list_deployments(self) -> List[Dict[str, Any]]:
        """
        List all deployments.
        
        Returns:
            List of deployment information
        """
        return [
            self.get_deployment_status(name)
            for name in self.deployments.keys()
        ]
    
    async def create_deployment_config(
        self,
        name: str,
        version: str,
        environment: str = "development"
    ) -> str:
        """
        Create a default deployment configuration file.
        
        Args:
            name: Deployment name
            version: Deployment version
            environment: Target environment
            
        Returns:
            Path to created configuration file
        """
        config = {
            'name': name,
            'version': version,
            'environment': environment,
            'replicas': 1,
            'services': [
                {
                    'name': 'postgres',
                    'version': '15-alpine',
                    'host': 'postgres',
                    'port': 5432,
                    'health_check_url': '/health',
                    'dependencies': [],
                    'metadata': {
                        'type': 'database',
                        'persistent': True
                    }
                },
                {
                    'name': 'redis',
                    'version': '7-alpine',
                    'host': 'redis',
                    'port': 6379,
                    'health_check_url': '/health',
                    'dependencies': [],
                    'metadata': {
                        'type': 'cache',
                        'persistent': False
                    }
                },
                {
                    'name': 'api',
                    'version': version,
                    'host': 'api',
                    'port': 8000,
                    'health_check_url': '/health',
                    'dependencies': ['postgres', 'redis'],
                    'metadata': {
                        'type': 'api',
                        'public': True
                    }
                },
                {
                    'name': 'worker',
                    'version': version,
                    'host': 'worker',
                    'port': 8001,
                    'health_check_url': '/health',
                    'dependencies': ['postgres', 'redis'],
                    'metadata': {
                        'type': 'worker',
                        'public': False
                    }
                },
                {
                    'name': 'web',
                    'version': version,
                    'host': 'web',
                    'port': 8501,
                    'health_check_url': '/health',
                    'dependencies': ['api'],
                    'metadata': {
                        'type': 'frontend',
                        'public': True
                    }
                }
            ],
            'resources': {
                'cpu_limit': '2000m',
                'memory_limit': '4Gi',
                'storage': '10Gi'
            },
            'health_checks': {
                'initial_delay': 30,
                'period': 10,
                'timeout': 5,
                'failure_threshold': 3
            }
        }
        
        config_path = f"deployments/{name}-{environment}.yml"
        config_dir = Path("deployments")
        config_dir.mkdir(exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        logger.info(f"Created deployment configuration: {config_path}")
        return config_path
    
    async def validate_deployment_config(self, config: DeploymentConfig) -> List[str]:
        """
        Validate a deployment configuration.
        
        Args:
            config: Deployment configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not config.name:
            errors.append("Deployment name is required")
        
        if not config.version:
            errors.append("Deployment version is required")
        
        if not config.services:
            errors.append("At least one service is required")
        
        # Validate services
        service_names = set()
        for service in config.services:
            if 'name' not in service:
                errors.append("Service name is required")
                continue
            
            service_name = service['name']
            if service_name in service_names:
                errors.append(f"Duplicate service name: {service_name}")
            service_names.add(service_name)
            
            # Check dependencies
            for dep in service.get('dependencies', []):
                if dep not in service_names and dep not in [s['name'] for s in config.services]:
                    errors.append(f"Service {service_name} has unknown dependency: {dep}")
        
        return errors


# Global deployment manager instance
deployment_manager = DeploymentManager(service_registry, health_monitor)