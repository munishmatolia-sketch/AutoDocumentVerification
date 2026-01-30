#!/bin/bash

# Kubernetes deployment script for document forensics system
set -e

# Configuration
NAMESPACE="document-forensics"
KUBECTL_TIMEOUT="300s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if we can connect to cluster
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_success "kubectl is available and connected to cluster"
}

# Check if required files exist
check_files() {
    local files=(
        "k8s/namespace.yaml"
        "k8s/configmap.yaml"
        "k8s/secrets.yaml"
        "k8s/postgres.yaml"
        "k8s/redis.yaml"
        "k8s/api.yaml"
        "k8s/worker.yaml"
        "k8s/web.yaml"
        "k8s/ingress.yaml"
    )
    
    for file in "${files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Required file not found: $file"
            exit 1
        fi
    done
    
    log_success "All required Kubernetes manifests found"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace: $NAMESPACE"
    kubectl apply -f k8s/namespace.yaml
    
    # Wait for namespace to be ready
    kubectl wait --for=condition=Ready namespace/$NAMESPACE --timeout=$KUBECTL_TIMEOUT
    log_success "Namespace created successfully"
}

# Deploy configuration and secrets
deploy_config() {
    log_info "Deploying configuration and secrets"
    kubectl apply -f k8s/configmap.yaml
    kubectl apply -f k8s/secrets.yaml
    log_success "Configuration and secrets deployed"
}

# Deploy database
deploy_database() {
    log_info "Deploying PostgreSQL database"
    kubectl apply -f k8s/postgres.yaml
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    kubectl wait --for=condition=Ready pod -l app=postgres -n $NAMESPACE --timeout=$KUBECTL_TIMEOUT
    
    # Wait for service to be ready
    kubectl wait --for=condition=Ready service/postgres-service -n $NAMESPACE --timeout=$KUBECTL_TIMEOUT
    
    log_success "PostgreSQL database deployed and ready"
}

# Deploy Redis
deploy_redis() {
    log_info "Deploying Redis cache"
    kubectl apply -f k8s/redis.yaml
    
    # Wait for Redis to be ready
    log_info "Waiting for Redis to be ready..."
    kubectl wait --for=condition=Ready pod -l app=redis -n $NAMESPACE --timeout=$KUBECTL_TIMEOUT
    
    # Wait for service to be ready
    kubectl wait --for=condition=Ready service/redis-service -n $NAMESPACE --timeout=$KUBECTL_TIMEOUT
    
    log_success "Redis cache deployed and ready"
}

# Deploy API
deploy_api() {
    log_info "Deploying API service"
    kubectl apply -f k8s/api.yaml
    
    # Wait for API to be ready
    log_info "Waiting for API service to be ready..."
    kubectl wait --for=condition=Available deployment/api -n $NAMESPACE --timeout=$KUBECTL_TIMEOUT
    
    # Wait for service to be ready
    kubectl wait --for=condition=Ready service/api-service -n $NAMESPACE --timeout=$KUBECTL_TIMEOUT
    
    log_success "API service deployed and ready"
}

# Deploy workers
deploy_workers() {
    log_info "Deploying worker services"
    kubectl apply -f k8s/worker.yaml
    
    # Wait for workers to be ready
    log_info "Waiting for worker services to be ready..."
    kubectl wait --for=condition=Available deployment/worker -n $NAMESPACE --timeout=$KUBECTL_TIMEOUT
    kubectl wait --for=condition=Available deployment/scheduler -n $NAMESPACE --timeout=$KUBECTL_TIMEOUT
    
    log_success "Worker services deployed and ready"
}

# Deploy web interface
deploy_web() {
    log_info "Deploying web interface"
    kubectl apply -f k8s/web.yaml
    
    # Wait for web interface to be ready
    log_info "Waiting for web interface to be ready..."
    kubectl wait --for=condition=Available deployment/web -n $NAMESPACE --timeout=$KUBECTL_TIMEOUT
    
    # Wait for service to be ready
    kubectl wait --for=condition=Ready service/web-service -n $NAMESPACE --timeout=$KUBECTL_TIMEOUT
    
    log_success "Web interface deployed and ready"
}

# Deploy ingress
deploy_ingress() {
    log_info "Deploying ingress and monitoring"
    kubectl apply -f k8s/ingress.yaml
    
    # Wait for flower monitoring to be ready
    log_info "Waiting for monitoring services to be ready..."
    kubectl wait --for=condition=Available deployment/flower -n $NAMESPACE --timeout=$KUBECTL_TIMEOUT
    
    log_success "Ingress and monitoring deployed"
}

# Perform health checks
health_check() {
    log_info "Performing health checks..."
    
    # Check all deployments
    local deployments=("postgres" "redis" "api" "worker" "scheduler" "web" "flower")
    
    for deployment in "${deployments[@]}"; do
        if kubectl get deployment $deployment -n $NAMESPACE &> /dev/null; then
            local ready=$(kubectl get deployment $deployment -n $NAMESPACE -o jsonpath='{.status.readyReplicas}')
            local desired=$(kubectl get deployment $deployment -n $NAMESPACE -o jsonpath='{.spec.replicas}')
            
            if [[ "$ready" == "$desired" ]]; then
                log_success "$deployment: $ready/$desired replicas ready"
            else
                log_warning "$deployment: $ready/$desired replicas ready"
            fi
        fi
    done
    
    # Test API health endpoint
    log_info "Testing API health endpoint..."
    if kubectl exec -n $NAMESPACE deployment/api -- curl -f http://localhost:8000/health &> /dev/null; then
        log_success "API health check passed"
    else
        log_warning "API health check failed"
    fi
}

# Display deployment status
show_status() {
    log_info "Deployment Status Summary:"
    echo
    
    # Show pods
    echo "Pods:"
    kubectl get pods -n $NAMESPACE -o wide
    echo
    
    # Show services
    echo "Services:"
    kubectl get services -n $NAMESPACE
    echo
    
    # Show ingress
    echo "Ingress:"
    kubectl get ingress -n $NAMESPACE
    echo
    
    # Show persistent volumes
    echo "Persistent Volume Claims:"
    kubectl get pvc -n $NAMESPACE
    echo
}

# Get service URLs
show_urls() {
    log_info "Service URLs:"
    
    # Get ingress info
    local ingress_ip=$(kubectl get ingress document-forensics-ingress -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
    
    if [[ "$ingress_ip" != "pending" && "$ingress_ip" != "" ]]; then
        echo "  API: https://api.document-forensics.example.com"
        echo "  Web Interface: https://web.document-forensics.example.com"
    else
        echo "  Ingress IP: $ingress_ip (configure DNS when available)"
    fi
    
    # Port forwarding instructions
    echo
    log_info "For local access, use port forwarding:"
    echo "  API: kubectl port-forward -n $NAMESPACE service/api-service 8000:8000"
    echo "  Web: kubectl port-forward -n $NAMESPACE service/web-service 8501:8501"
    echo "  Flower: kubectl port-forward -n $NAMESPACE service/flower-service 5555:5555"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up deployment..."
    
    # Delete all resources in namespace
    kubectl delete namespace $NAMESPACE --ignore-not-found=true
    
    log_success "Cleanup completed"
}

# Main deployment function
deploy() {
    log_info "Starting deployment of Document Forensics System"
    
    check_kubectl
    check_files
    
    create_namespace
    deploy_config
    deploy_database
    deploy_redis
    deploy_api
    deploy_workers
    deploy_web
    deploy_ingress
    
    health_check
    show_status
    show_urls
    
    log_success "Deployment completed successfully!"
}

# Script usage
usage() {
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  deploy    Deploy the complete system (default)"
    echo "  cleanup   Remove all deployed resources"
    echo "  status    Show current deployment status"
    echo "  health    Perform health checks"
    echo "  urls      Show service URLs"
    echo "  help      Show this help message"
    echo
}

# Main script logic
case "${1:-deploy}" in
    deploy)
        deploy
        ;;
    cleanup)
        cleanup
        ;;
    status)
        show_status
        ;;
    health)
        health_check
        ;;
    urls)
        show_urls
        ;;
    help)
        usage
        ;;
    *)
        log_error "Unknown command: $1"
        usage
        exit 1
        ;;
esac