#!/usr/bin/env python3
"""
System startup script for the document forensics system.

This script provides various ways to start the system components.
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from document_forensics.integration.system_integrator import system_integrator
from document_forensics.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def start_complete_system():
    """Start the complete document forensics system."""
    logger.info("Starting complete Document Forensics System...")
    
    try:
        await system_integrator.run_system(start_api=True)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"System error: {str(e)}")
    finally:
        await system_integrator.shutdown()


async def start_api_only():
    """Start only the API server."""
    logger.info("Starting API server only...")
    
    try:
        # Initialize system without starting full monitoring
        if await system_integrator.initialize_system():
            # Start API server
            if await system_integrator.start_api_server():
                logger.info("API server is running. Press Ctrl+C to stop.")
                
                # Wait for shutdown signal
                await system_integrator.shutdown_event.wait()
            else:
                logger.error("Failed to start API server")
        else:
            logger.error("System initialization failed")
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"API server error: {str(e)}")
    finally:
        await system_integrator.shutdown()


async def start_monitoring_only():
    """Start only the monitoring components."""
    logger.info("Starting monitoring components only...")
    
    try:
        # Initialize system
        if await system_integrator.initialize_system():
            logger.info("Monitoring is running. Press Ctrl+C to stop.")
            
            # Display status periodically
            while system_integrator.running:
                await asyncio.sleep(30)
                
                # Get and display system status
                health_status = await system_integrator.health_monitor.perform_immediate_check()
                registry_status = system_integrator.service_registry.get_registry_status()
                
                logger.info(f"Health: {health_status['status']} | Services: {registry_status['healthy_services']}/{registry_status['total_services']}")
        else:
            logger.error("System initialization failed")
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"Monitoring error: {str(e)}")
    finally:
        await system_integrator.shutdown()


async def check_system_status():
    """Check and display current system status."""
    logger.info("Checking system status...")
    
    try:
        # Initialize system briefly
        if await system_integrator.initialize_system():
            
            # Get comprehensive status
            system_info = system_integrator.get_system_info()
            
            print("\n=== Document Forensics System Status ===")
            print(f"System Running: {system_info['running']}")
            print(f"Log Level: {system_info['settings']['log_level']}")
            print(f"Max File Size: {system_info['settings']['max_file_size']} bytes")
            
            print("\nComponents:")
            for component, status in system_info['components'].items():
                status_symbol = "✓" if status else "✗"
                print(f"  {status_symbol} {component}")
            
            print(f"\nServices: {system_info['service_registry']['healthy_services']}/{system_info['service_registry']['total_services']} healthy")
            
            if system_info['service_registry']['services']:
                print("\nService Details:")
                for service_name, service_info in system_info['service_registry']['services'].items():
                    status_symbol = "✓" if service_info['status'] == 'healthy' else "✗"
                    print(f"  {status_symbol} {service_name}: {service_info['host']}:{service_info['port']}")
            
            print(f"\nActive Batches: {system_info['workflow_manager']['active_batches']}")
            print(f"Active Documents: {system_info['workflow_manager']['active_documents']}")
            print("========================================\n")
            
        else:
            print("Failed to initialize system for status check")
            
    except Exception as e:
        logger.error(f"Status check error: {str(e)}")
    finally:
        await system_integrator.shutdown()


async def run_health_check():
    """Run a comprehensive health check."""
    logger.info("Running health check...")
    
    try:
        # Initialize system briefly
        if await system_integrator.initialize_system():
            
            # Perform health check
            health_status = await system_integrator.health_monitor.perform_immediate_check()
            
            print(f"\n=== Health Check Results ===")
            print(f"Overall Status: {health_status['status'].upper()}")
            print(f"Message: {health_status['message']}")
            print(f"Last Check: {health_status['last_check']}")
            
            print("\nComponent Health:")
            for component_name, component_info in health_status['components'].items():
                status_symbol = "✓" if component_info['status'] == 'healthy' else "✗"
                print(f"  {status_symbol} {component_name}: {component_info['status']}")
                
                if component_info['error_message']:
                    print(f"    Error: {component_info['error_message']}")
                
                if component_info['metrics']:
                    print(f"    Metrics:")
                    for metric in component_info['metrics']:
                        print(f"      - {metric['name']}: {metric['value']} {metric['unit']} ({metric['status']})")
            
            print("============================\n")
            
            # Exit with appropriate code
            is_healthy = health_status['status'] == 'healthy'
            sys.exit(0 if is_healthy else 1)
            
        else:
            print("Failed to initialize system for health check")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        sys.exit(1)
    finally:
        await system_integrator.shutdown()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Document Forensics System Startup")
    parser.add_argument('mode', choices=['full', 'api', 'monitor', 'status', 'health'],
                       help='Startup mode')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Log level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Run appropriate mode
    if args.mode == 'full':
        asyncio.run(start_complete_system())
    elif args.mode == 'api':
        asyncio.run(start_api_only())
    elif args.mode == 'monitor':
        asyncio.run(start_monitoring_only())
    elif args.mode == 'status':
        asyncio.run(check_system_status())
    elif args.mode == 'health':
        asyncio.run(run_health_check())


if __name__ == '__main__':
    main()