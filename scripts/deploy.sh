# ============================================================
# Deployment Automation Script
# ============================================================
# Hermes AGI/ASI Harness - Automated Deployment Script
# Usage: ./scripts/deploy.sh --environment <staging|production>
# ============================================================

#!/usr/bin/env bash
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="staging"
IMAGE_TAG=""
SKIP_TESTS=false
FORCE_DEPLOY=false
TIMEOUT=300
CANARY_TRAFFIC_PERCENT=10

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ============================================================
# Functions
# ============================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date -u +%Y-%m-%dT%H:%M:%SZ) $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Hermes AGI/ASI Harness Deployment Script

Options:
    -e, --environment ENV     Target environment (staging|production) [default: staging]
    -t, --tag TAG             Docker image tag to deploy
    -s, --skip-tests          Skip smoke tests
    -f, --force               Force deployment even if canary fails
    --timeout SECONDS         Deployment timeout in seconds [default: 300]
    --canary-percent PERCENT  Canary traffic percentage [default: 10]
    -h, --help                Show this help message

Examples:
    ./scripts/deploy.sh --environment staging --tag sha-abc123
    ./scripts/deploy.sh --environment production --tag v1.2.3 --canary-percent 20
EOF
    exit 0
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -e|--environment)
                ENVIRONMENT="$2"
                shift 2
                ;;
            -t|--tag)
                IMAGE_TAG="$2"
                shift 2
                ;;
            -s|--skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            -f|--force)
                FORCE_DEPLOY=true
                shift
                ;;
            --timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            --canary-percent)
                CANARY_TRAFFIC_PERCENT="$2"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                ;;
        esac
    done
}

validate_environment() {
    if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
        log_error "Invalid environment: $ENVIRONMENT. Must be 'staging' or 'production'."
        exit 1
    fi

    if [[ -z "$IMAGE_TAG" ]]; then
        log_error "Image tag is required. Use --tag <tag>"
        exit 1
    fi
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    local required_tools=("kubectl" "helm" "aws" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &>/dev/null; then
            log_error "$tool is required but not installed."
            exit 1
        fi
    done

    # Verify AWS credentials
    if ! aws sts get-caller-identity &>/dev/null; then
        log_error "AWS credentials not configured."
        exit 1
    fi

    log_success "All prerequisites met."
}

deploy_infrastructure() {
    log_info "Deploying infrastructure for $ENVIRONMENT..."

    cd "$PROJECT_ROOT/infrastructure/terraform"

    terraform init -backend-config="key=tfstate/${ENVIRONMENT}/terraform.tfstate"
    terraform workspace select "$ENVIRONMENT" 2>/dev/null || terraform workspace new "$ENVIRONMENT"

    terraform plan \
        -var="environment=$ENVIRONMENT" \
        -out=tfplan

    terraform apply -auto-approve tfplan

    log_success "Infrastructure deployed."
}

deploy_application() {
    log_info "Deploying application to $ENVIRONMENT..."

    local namespace="hermes-$ENVIRONMENT"

    # Update kubeconfig
    aws eks update-kubeconfig \
        --name "hermes-$ENVIRONMENT" \
        --region us-east-1

    # Apply Kubernetes manifests
    kubectl apply -f "$PROJECT_ROOT/infrastructure/k8s/staging.yaml"
    if [[ "$ENVIRONMENT" == "production" ]]; then
        kubectl apply -f "$PROJECT_ROOT/infrastructure/k8s/production.yaml"
    fi

    # Update image
    kubectl set image deployment/hermes-app \
        app="ghcr.io/itsPremkumar/hermes-agi-asi-harness:${IMAGE_TAG}" \
        -n "$namespace"

    # Wait for rollout
    kubectl rollout status deployment/hermes-app \
        -n "$namespace" \
        --timeout="${TIMEOUT}s"

    log_success "Application deployed."
}

run_canary_analysis() {
    if [[ "$ENVIRONMENT" != "production" ]]; then
        log_info "Skipping canary analysis for non-production environment."
        return 0
    fi

    log_info "Running canary analysis..."

    local namespace="hermes-production"
    local duration=300  # 5 minutes
    local error_threshold=1  # 1%
    local latency_threshold=500  # 500ms

    # Route small percentage of traffic to canary
    kubectl annotate ingress hermes-app-ingress \
        nginx.ingress.kubernetes.io/canary-weight="$CANARY_TRAFFIC_PERCENT" \
        -n "$namespace" --overwrite

    log_info "Routing ${CANARY_TRAFFIC_PERCENT}% traffic to canary for ${duration}s..."

    sleep "$duration"

    # Check error rate
    local error_rate
    error_rate=$(curl -s "http://prometheus:9090/api/v1/query?query=\
sum(rate(http_requests_total{status=~'5..',track='canary'}[5m]))\
/sum(rate(http_requests_total{track='canary'}[5m]))" | \
        jq -r '.data.result[0].value[1] // "0"')

    if (( $(echo "$error_rate > $error_threshold" | bc -l) )); then
        log_error "Canary failed: error rate ${error_rate} exceeds threshold ${error_threshold}%"
        if [[ "$FORCE_DEPLOY" != true ]]; then
            rollback_canary
            exit 1
        fi
    fi

    # Check latency
    local p99_latency
    p99_latency=$(curl -s "http://prometheus:9090/api/v1/query?query=\
histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{track='canary'}[5m]))" | \
        jq -r '.data.result[0].value[1] // "0"')

    if (( $(echo "$p99_latency > $latency_threshold" | bc -l) )); then
        log_error "Canary failed: p99 latency ${p99_latency}ms exceeds threshold ${latency_threshold}ms"
        if [[ "$FORCE_DEPLOY" != true ]]; then
            rollback_canary
            exit 1
        fi
    fi

    log_success "Canary analysis passed. Promoting to full rollout..."

    # Remove canary annotation and promote
    kubectl annotate ingress hermes-app-ingress \
        nginx.ingress.kubernetes.io/canary-weight- \
        -n "$namespace"

    # Scale down canary
    kubectl scale deployment/hermes-app-canary --replicas=0 -n "$namespace"
}

rollback_canary() {
    log_warn "Rolling back canary deployment..."

    kubectl annotate ingress hermes-app-ingress \
        nginx.ingress.kubernetes.io/canary-weight- \
        -n hermes-production

    kubectl scale deployment/hermes-app-canary --replicas=0 -n hermes-production

    log_success "Canary rolled back."
}

rollback() {
    log_warn "Rolling back deployment..."

    kubectl rollout undo deployment/hermes-app -n "hermes-$ENVIRONMENT"
    kubectl rollout status deployment/hermes-app -n "hermes-$ENVIRONMENT" --timeout="${TIMEOUT}s"

    log_success "Rollback complete."
}

run_smoke_tests() {
    if [[ "$SKIP_TESTS" == true ]]; then
        log_info "Skipping smoke tests."
        return 0
    fi

    log_info "Running smoke tests..."

    local base_url
    if [[ "$ENVIRONMENT" == "production" ]]; then
        base_url="https://hermes-agi-asi-harness.dev"
    else
        base_url="https://staging.hermes-agi-asi-harness.dev"
    fi

    # Health check
    local health_status
    health_status=$(curl -s -o /dev/null -w "%{http_code}" "${base_url}/health")
    if [[ "$health_status" -ne 200 ]]; then
        log_error "Health check failed with status: $health_status"
        return 1
    fi

    # API readiness
    local ready_status
    ready_status=$(curl -s -o /dev/null -w "%{http_code}" "${base_url}/ready")
    if [[ "$ready_status" -ne 200 ]]; then
        log_error "Readiness check failed with status: $ready_status"
        return 1
    fi

    log_success "Smoke tests passed."
}

notify_deployment() {
    local status="${1:-success}"
    local message

    if [[ "$status" == "success" ]]; then
        message="Deployment to $ENVIRONMENT succeeded: $IMAGE_TAG"
    else
        message="Deployment to $ENVIRONMENT failed: $IMAGE_TAG"
    fi

    # Slack notification
    if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
        curl -s -X POST "$SLACK_WEBHOOK_URL" \
            -H 'Content-Type: application/json' \
            -d "{\"text\": \"$message\"}" || true
    fi

    # GitHub Actions summary
    if [[ -n "${GITHUB_STEP_SUMMARY:-}" ]]; then
        echo "## Deployment $status" >> "$GITHUB_STEP_SUMMARY"
        echo "- Environment: $ENVIRONMENT" >> "$GITHUB_STEP_SUMMARY"
        echo "- Image: $IMAGE_TAG" >> "$GITHUB_STEP_SUMMARY"
        echo "- Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$GITHUB_STEP_SUMMARY"
    fi
}

cleanup() {
    log_info "Cleaning up temporary files..."
    rm -f "$PROJECT_ROOT/infrastructure/terraform/tfplan"
}

# ============================================================
# Main
# ============================================================

main() {
    parse_args "$@"
    validate_environment
    check_prerequisites

    log_info "Starting deployment to $ENVIRONMENT..."
    log_info "Image tag: $IMAGE_TAG"

    # Trap for cleanup
    trap cleanup EXIT

    # Deploy
    deploy_infrastructure
    deploy_application

    # Canary (production only)
    if [[ "$ENVIRONMENT" == "production" ]]; then
        run_canary_analysis
    fi

    # Smoke tests
    run_smoke_tests

    # Notify
    notify_deployment "success"

    log_success "Deployment to $ENVIRONMENT completed successfully!"
}

main "$@"
