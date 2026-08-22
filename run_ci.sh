#!/usr/bin/env bash
# ==============================================================================
# run_ci.sh - Local CI Runner for tvtv2xmltv
# Mirrors the GitHub Actions CI workflow (.github/workflows/ci.yml)
# Compatible with Bash 3.2+ (macOS default) and Bash 4/5+ (Linux)
# ==============================================================================

set -uo pipefail

# Determine repository root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Color formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# Results tracking (Bash 3.2 compatible parallel arrays)
STAGE_NAMES=()
STAGE_STATUSES=()
STAGE_DURATIONS=()
START_TOTAL=$(date +%s)

print_header() {
    echo -e "${BLUE}${BOLD}======================================================================${NC}"
    echo -e "${BLUE}${BOLD}  🚀 tvtv2xmltv - Local CI Pipeline${NC}"
    echo -e "${BLUE}${BOLD}======================================================================${NC}"
}

print_section() {
    echo ""
    echo -e "${CYAN}${BOLD}▶ $1${NC}"
    echo -e "${CYAN}----------------------------------------------------------------------${NC}"
}

print_success() {
    echo -e "${GREEN}✔ $1${NC}"
}

print_error() {
    echo -e "${RED}✖ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    if ! command -v uv &> /dev/null; then
        print_error "'uv' is not installed or not in PATH."
        echo "Please install uv: https://docs.astral.sh/uv/getting-started/installation/"
        exit 1
    fi
}

show_help() {
    echo "Usage: ./run_ci.sh [options]"
    echo ""
    echo "Options:"
    echo "  --all            Run all CI stages (default)"
    echo "  --lint           Run linting and code formatting checks only"
    echo "  --test           Run unit tests and code coverage only"
    echo "  --security       Run bandit and safety security scans only"
    echo "  --fix            Auto-format code with black before running checks"
    echo "  --install-hooks  Install git pre-commit hooks locally"
    echo "  -h, --help       Show this help message"
    echo ""
}

# Install git pre-commit hooks
install_hooks() {
    print_section "Installing Git Pre-Commit Hooks"
    if uv run pre-commit install; then
        print_success "Pre-commit hooks installed successfully."
        return 0
    else
        print_error "Failed to install pre-commit hooks."
        return 1
    fi
}

# Track stage execution and timing
run_stage() {
    local stage_name="$1"
    local stage_func="$2"
    local start_time
    start_time=$(date +%s)

    local ret=0
    if $stage_func; then
        STAGE_STATUSES+=("PASS")
    else
        STAGE_STATUSES+=("FAIL")
        ret=1
    fi

    local end_time
    end_time=$(date +%s)
    local duration=$((end_time - start_time))
    STAGE_NAMES+=("$stage_name")
    STAGE_DURATIONS+=("$duration")

    return $ret
}

# Auto-format code
format_code() {
    print_section "Auto-formatting Code with Black"
    if uv run black src/ tests/; then
        print_success "Code formatted successfully."
        return 0
    else
        print_error "Black formatting failed."
        return 1
    fi
}

# Stage 1: Linting & Code Style
stage_lint() {
    local failed=0
    print_section "Stage 1: Linting & Code Formatting"

    echo "1. Checking for Python syntax errors and undefined names (flake8)..."
    if uv run flake8 src/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics; then
        print_success "Flake8 syntax check passed."
    else
        print_error "Flake8 syntax check found critical issues."
        failed=1
    fi

    echo ""
    echo "2. Checking complexity and code style warnings (flake8)..."
    uv run flake8 src/ tests/ --count --exit-zero --max-complexity=10 --max-line-length=100 --statistics

    echo ""
    echo "3. Verifying code formatting with Black..."
    if uv run black --check src/ tests/; then
        print_success "Black format check passed."
    else
        print_error "Black format check failed. Run './run_ci.sh --fix' to format automatically."
        failed=1
    fi

    return $failed
}

# Stage 2: Tests & Coverage
stage_test() {
    local failed=0
    print_section "Stage 2: Pytest Suite & Code Coverage"

    echo "Running pytest with coverage..."
    if PYTHONPATH=src uv run pytest tests/ -v --cov=tvtv2xmltv --cov-report=xml --cov-report=term; then
        print_success "All unit tests and coverage checks passed."
    else
        print_error "Pytest suite failed."
        failed=1
    fi

    return $failed
}

# Stage 3: Security Scans
stage_security() {
    local failed=0
    print_section "Stage 3: Security Analysis (Bandit & Safety)"

    echo "1. Running Bandit AST security scan on src/..."
    if uv run --with bandit bandit -r src/ -f json -o bandit-report.json > /dev/null 2>&1 && \
       uv run --with bandit bandit -r src/ -f screen; then
        print_success "Bandit security check passed."
    else
        print_warning "Bandit reported warnings (non-blocking in CI)."
    fi

    echo ""
    echo "2. Running Safety vulnerability scan on dependencies..."
    local pkg_file
    pkg_file=$(mktemp /tmp/tvtv-packages.XXXXXX)
    uv pip freeze > "$pkg_file" 2>/dev/null || true

    if uv run --with safety safety check --file "$pkg_file" 2>&1; then
        print_success "Safety check completed with no issues."
    else
        print_warning "Safety check completed with advisories (non-blocking in CI)."
    fi
    rm -f "$pkg_file"

    return $failed
}

# Print summary
print_summary() {
    local end_total
    end_total=$(date +%s)
    local total_duration=$((end_total - START_TOTAL))
    local any_failed=0

    echo ""
    echo -e "${BLUE}${BOLD}======================================================================${NC}"
    echo -e "${BLUE}${BOLD}  📊 CI Summary Report${NC}"
    echo -e "${BLUE}${BOLD}======================================================================${NC}"

    printf "%-35s %-12s %-10s\n" "Stage" "Status" "Duration"
    echo "----------------------------------------------------------------------"

    local total_stages=${#STAGE_NAMES[@]}
    local i=0
    while [ $i -lt $total_stages ]; do
        local name="${STAGE_NAMES[$i]}"
        local status="${STAGE_STATUSES[$i]}"
        local duration="${STAGE_DURATIONS[$i]}s"

        if [ "$status" = "PASS" ]; then
            printf "%-35s ${GREEN}%-12s${NC} %-10s\n" "$name" "✔ PASS" "$duration"
        else
            printf "%-35s ${RED}%-12s${NC} %-10s\n" "$name" "✖ FAIL" "$duration"
            any_failed=1
        fi
        i=$((i + 1))
    done

    echo "----------------------------------------------------------------------"
    echo "Total Time: ${total_duration}s"
    echo ""

    if [ $any_failed -eq 0 ]; then
        echo -e "${GREEN}${BOLD}🎉 ALL CI CHECKS PASSED!${NC}"
        return 0
    else
        echo -e "${RED}${BOLD}❌ CI CHECKS FAILED. Please review the errors above.${NC}"
        return 1
    fi
}

# Main entry point
main() {
    check_prerequisites
    print_header

    local RUN_ALL=true
    local RUN_LINT=false
    local RUN_TEST=false
    local RUN_SECURITY=false
    local DO_FIX=false

    if [ $# -gt 0 ]; then
        RUN_ALL=false
        while [ $# -gt 0 ]; do
            case "$1" in
                --all)
                    RUN_ALL=true
                    shift
                    ;;
                --lint)
                    RUN_LINT=true
                    shift
                    ;;
                --test)
                    RUN_TEST=true
                    shift
                    ;;
                --security)
                    RUN_SECURITY=true
                    shift
                    ;;
                --fix|--format)
                    DO_FIX=true
                    shift
                    ;;
                --install-hooks)
                    install_hooks
                    exit $?
                    ;;
                -h|--help)
                    show_help
                    exit 0
                    ;;
                *)
                    print_error "Unknown option: $1"
                    show_help
                    exit 1
                    ;;
            esac
        done
    fi

    if [ "$DO_FIX" = true ]; then
        format_code
    fi

    local overall_exit=0

    if [ "$RUN_ALL" = true ] || [ "$RUN_LINT" = true ]; then
        if ! run_stage "Stage 1: Lint & Formatting" stage_lint; then
            overall_exit=1
        fi
    fi

    if [ "$RUN_ALL" = true ] || [ "$RUN_TEST" = true ]; then
        if ! run_stage "Stage 2: Pytest & Coverage" stage_test; then
            overall_exit=1
        fi
    fi

    if [ "$RUN_ALL" = true ] || [ "$RUN_SECURITY" = true ]; then
        if ! run_stage "Stage 3: Security (Bandit/Safety)" stage_security; then
            overall_exit=1
        fi
    fi

    print_summary
    return $?
}

main "$@"
