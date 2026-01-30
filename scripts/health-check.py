#!/usr/bin/env python3
"""
Health check script for the document forensics system.

This script performs comprehensive health checks and can be used for monitoring.
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from document_forensics.integration.health_monitor import health_monitor
from document_forensics.integration.service_registry import service_registry


async def perform_health_check(output_format: str = 'text', detailed: bool = False) -> dict:
    """
    Perform comprehensive health check.
    
    Args:
        output_format: Output format ('text', 'json')
        detailed: Whether to include detailed metrics
        
    Returns:
        Health check results
    """
    # Get health status
    health_status = await health_monitor.perform_immediate_check()
    
    # Get service registry status
    registry_status = service_registry.get_registry_status()
    
    # Combine results
    results = {
        'timestamp': health_status.get('last_check'),
        'overall_status': health_status['status'],
        'message': health_status['message'],
        'monitoring_active': health_status['monitoring_active'],
        'system_health': health_status,
        'service_registry': registry_status
    }
    
    if output_format == 'json':
        print(json.dumps(results, indent=2))
    else:
        # Text output
        print(f"System Health Check - {results['timestamp']}")
        print(f"Overall Status: {results['overall_status'].upper()}")
        print(f"Message: {results['message']}")
        print(f"Monitoring Active: {results['monitoring_active']}")
        print()
        
        # Component health
        print("Component Health:")
        for component_name, component_info in health_status['components'].items():
            status_symbol = "✓" if component_info['status'] == 'healthy' else "✗"
            print(f"  {status_symbol} {component_name}: {component_info['status']}")
            
            if component_info['error_message']:
                print(f"    Error: {component_info['error_message']}")
            
            if detailed and component_info['metrics']:
                print(f"    Metrics:")
                for metric in component_info['metrics']:
                    print(f"      - {metric['name']}: {metric['value']} {metric['unit']} ({metric['status']})")
        
        print()
        
        # Service registry
        print("Service Registry:")
        print(f"  Total Services: {registry_status['total_services']}")
        print(f"  Healthy Services: {registry_status['healthy_services']}")
        print(f"  Unhealthy Services: {registry_status['unhealthy_services']}")
        
        if detailed and registry_status['services']:
            print("  Service Details:")
            for service_name, service_info in registry_status['services'].items():
                status_symbol = "✓" if service_info['status'] == 'healthy' else "✗"
                print(f"    {status_symbol} {service_name}: {service_info['status']}")
                print(f"      Host: {service_info['host']}:{service_info['port']}")
                print(f"      Version: {service_info['version']}")
                if service_info['last_health_check']:
                    print(f"      Last Check: {service_info['last_health_check']}")
    
    return results


async def wait_for_healthy(timeout: int = 60, check_interval: int = 5) -> bool:
    """
    Wait for system to become healthy.
    
    Args:
        timeout: Maximum time to wait in seconds
        check_interval: Time between checks in seconds
        
    Returns:
        True if system became healthy within timeout
    """
    import time
    
    start_time = time.time()
    
    print(f"Waiting for system to become healthy (timeout: {timeout}s)...")
    
    while time.time() - start_time < timeout:
        results = await perform_health_check(output_format='json', detailed=False)
        
        if results['overall_status'] == 'healthy':
            print("System is healthy!")
            return True
        
        print(f"Status: {results['overall_status']} - {results['message']}")
        await asyncio.sleep(check_interval)
    
    print("Timeout waiting for system to become healthy")
    return False


async def main():
    """Main health check script entry point."""
    parser = argparse.ArgumentParser(description="Document Forensics Health Check")
    parser.add_argument('--format', choices=['text', 'json'], default='text',
                       help='Output format')
    parser.add_argument('--detailed', action='store_true',
                       help='Include detailed metrics')
    parser.add_argument('--wait', type=int, metavar='SECONDS',
                       help='Wait for system to become healthy (timeout in seconds)')
    parser.add_argument('--check-interval', type=int, default=5,
                       help='Check interval when waiting (seconds)')
    
    args = parser.parse_args()
    
    try:
        if args.wait:
            success = await wait_for_healthy(timeout=args.wait, check_interval=args.check_interval)
            sys.exit(0 if success else 1)
        else:
            results = await perform_health_check(output_format=args.format, detailed=args.detailed)
            
            # Exit with non-zero code if system is not healthy
            is_healthy = results['overall_status'] == 'healthy'
            sys.exit(0 if is_healthy else 1)
            
    except Exception as e:
        if args.format == 'json':
            error_result = {
                'error': str(e),
                'overall_status': 'error'
            }
            print(json.dumps(error_result))
        else:
            print(f"Health check error: {str(e)}")
        
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())