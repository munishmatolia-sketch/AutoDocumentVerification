#!/usr/bin/env python3
"""
Deployment script for the document forensics system.

This script handles deployment orchestration, health checks, and rollback procedures.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from document_forensics.integration.deployment_manager import deployment_manager
from document_forensics.integration.service_registry import service_registry
from document_forensics.integration.health_monitor import health_monitor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def deploy_system(config_path: str, deployment_name: str) -> bool:
    """
    Deploy the document forensics system.
    
    Args:
        config_path: Path to deployment configuration
        deployment_name: Name for this deployment
        
    Returns:
        True if deployment successful
    """
    try:
        logger.info(f"Starting deployment: {deployment_name}")
        
        # Load deployment configuration
        config = deployment_manager.load_deployment_config(config_path)
        logger.info(f"Loaded configuration for {config.name} v{config.version}")
        
        # Validate configuration
        errors = await deployment_manager.validate_deployment_config(config)
        if errors:
            logger.error("Configuration validation failed:")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        
        # Deploy the system
        success = await deployment_manager.deploy(deployment_name, config)
        
        if success:
            logger.info("Deployment completed successfully")
            
            # Display deployment status
            status = deployment_manager.get_deployment_status(deployment_name)
            if status:
                logger.info(f"Deployment Status: {status['status']}")
                logger.info(f"Services: {len(status['services'])}")
                for service_name, service_info in status['service_health'].items():
                    logger.info(f"  - {service_name}: {service_info['status']}")
        else:
            logger.error("Deployment failed")
            
        return success
        
    except Exception as e:
        logger.error(f"Deployment error: {str(e)}")
        return False


async def stop_deployment(deployment_name: str) -> bool:
    """
    Stop a running deployment.
    
    Args:
        deployment_name: Name of deployment to stop
        
    Returns:
        True if stopped successfully
    """
    try:
        logger.info(f"Stopping deployment: {deployment_name}")
        
        success = await deployment_manager.stop_deployment(deployment_name)
        
        if success:
            logger.info("Deployment stopped successfully")
        else:
            logger.error("Failed to stop deployment")
            
        return success
        
    except Exception as e:
        logger.error(f"Stop deployment error: {str(e)}")
        return False


async def check_health() -> bool:
    """
    Check system health.
    
    Returns:
        True if system is healthy
    """
    try:
        logger.info("Checking system health...")
        
        # Get overall health status
        health_status = await health_monitor.perform_immediate_check()
        
        logger.info(f"Overall Status: {health_status['status']}")
        logger.info(f"Message: {health_status['message']}")
        
        # Display component health
        for component_name, component_info in health_status['components'].items():
            logger.info(f"Component {component_name}: {component_info['status']}")
            if component_info['error_message']:
                logger.warning(f"  Error: {component_info['error_message']}")
        
        # Get service registry status
        registry_status = service_registry.get_registry_status()
        logger.info(f"Services: {registry_status['healthy_services']}/{registry_status['total_services']} healthy")
        
        return health_status['status'] == 'healthy'
        
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return False


async def list_deployments():
    """List all deployments."""
    try:
        deployments = deployment_manager.list_deployments()
        
        if not deployments:
            logger.info("No deployments found")
            return
        
        logger.info(f"Found {len(deployments)} deployment(s):")
        for deployment in deployments:
            logger.info(f"  - {deployment['name']}: {deployment['status']}")
            logger.info(f"    Version: {deployment['config']['version']}")
            logger.info(f"    Environment: {deployment['config']['environment']}")
            logger.info(f"    Services: {len(deployment['services'])}")
            
    except Exception as e:
        logger.error(f"List deployments error: {str(e)}")


async def create_config(name: str, version: str, environment: str) -> str:
    """
    Create a deployment configuration file.
    
    Args:
        name: Deployment name
        version: Version
        environment: Target environment
        
    Returns:
        Path to created configuration file
    """
    try:
        config_path = await deployment_manager.create_deployment_config(
            name=name,
            version=version,
            environment=environment
        )
        
        logger.info(f"Created deployment configuration: {config_path}")
        return config_path
        
    except Exception as e:
        logger.error(f"Create config error: {str(e)}")
        return ""


async def main():
    """Main deployment script entry point."""
    parser = argparse.ArgumentParser(description="Document Forensics Deployment Manager")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Deploy command
    deploy_parser = subparsers.add_parser('deploy', help='Deploy the system')
    deploy_parser.add_argument('--config', required=True, help='Path to deployment configuration')
    deploy_parser.add_argument('--name', required=True, help='Deployment name')
    
    # Stop command
    stop_parser = subparsers.add_parser('stop', help='Stop a deployment')
    stop_parser.add_argument('--name', required=True, help='Deployment name')
    
    # Health command
    health_parser = subparsers.add_parser('health', help='Check system health')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List deployments')
    
    # Create config command
    config_parser = subparsers.add_parser('create-config', help='Create deployment configuration')
    config_parser.add_argument('--name', required=True, help='Deployment name')
    config_parser.add_argument('--version', required=True, help='Version')
    config_parser.add_argument('--environment', default='development', help='Environment')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    success = True
    
    if args.command == 'deploy':
        success = await deploy_system(args.config, args.name)
    elif args.command == 'stop':
        success = await stop_deployment(args.name)
    elif args.command == 'health':
        success = await check_health()
    elif args.command == 'list':
        await list_deployments()
    elif args.command == 'create-config':
        config_path = await create_config(args.name, args.version, args.environment)
        success = bool(config_path)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())