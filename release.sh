#!/usr/bin/env bash
# ==============================================================================
# release.sh - GitHub Actions-Driven Release Automation for tvtv2xmltv
# Validates, synchronizes versioning, creates Git release tags, and pushes
# to trigger GitHub Actions image build & publish workflow (.github/workflows/docker.yml).
# Compatible with Bash 3.2+ (macOS default) and Bash 4/5+ (Linux)
# ==============================================================================

set -uo pipefail

# Determine repository root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Color formatting (matches run_ci.sh style)
BOLD="\033[1m"
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
CYAN="\033[0;36m"
BLUE="\033[0;34m"
MAGENTA="\033[0;35m"
NC="\033[0m" # No Color

print_header() {
    echo -e "${BLUE}${BOLD}======================================================================${NC}"
    echo -e "${BLUE}${BOLD}  🚀 tvtv2xmltv - Release & Tagging Automation${NC}"
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

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

show_help() {
    cat << 'EOF'
Usage: ./release.sh [VERSION | OPTIONS]

Creates a new versioned release tag and pushes it to GitHub, triggering
the GitHub Actions workflow (.github/workflows/docker.yml) to build, test,
and publish the container image to GitHub Container Registry (ghcr.io).

Arguments:
  VERSION                     Release version (e.g., 1.1.0 or v1.1.0).
                              If omitted, detects current version or prompts.

Version Bump Options:
  --patch                     Bump patch version (e.g. 1.0.0 -> 1.0.1)
  --minor                     Bump minor version (e.g. 1.0.0 -> 1.1.0)
  --major                     Bump major version (e.g. 1.0.0 -> 2.0.0)
  -v, --version <VERSION>     Explicitly specify target release version

Release Options:
  -m, --message <MESSAGE>     Custom release message / tag annotation
  -w, --watch                 Watch the triggered GitHub Actions workflow (requires gh CLI)
  --no-push                   Tag locally without pushing to remote origin
  --allow-dirty               Allow release with uncommitted changes in working tree
  --allow-branch              Allow release from branches other than main/master

Quality & Execution Options:
  --skip-tests, --no-test     Skip running pre-release lint and test checks locally
  -n, --dry-run               Simulate release steps without modifying files, tagging, or pushing
  -y, --yes, --non-interactive
                              Skip all interactive confirmation prompts
  -h, --help                  Display this help message and exit

Examples:
  ./release.sh --dry-run                 # Preview release steps without making changes
  ./release.sh --patch                   # Bump patch (1.0.0 -> 1.0.1), tag, and push to trigger Actions
  ./release.sh --minor                   # Bump minor (1.0.0 -> 1.1.0), tag, and push
  ./release.sh 1.1.0                     # Release version 1.1.0
  ./release.sh 1.1.0 --watch             # Release and stream the GitHub Actions workflow execution
  ./release.sh 1.1.0 --no-push           # Create version bump and tag locally only
EOF
}

# Defaults
VERSION=""
BUMP_TYPE=""
RELEASE_MESSAGE=""
PUSH_TO_REMOTE=true
RUN_TESTS=true
WATCH_WORKFLOW=false
ALLOW_DIRTY=false
ALLOW_BRANCH=false
DRY_RUN=false
AUTO_CONFIRM=false
REPO_SLUG=""

# Parse command line arguments
parse_args() {
    while [ $# -gt 0 ]; do
        case "$1" in
            -h|--help)
                show_help
                exit 0
                ;;
            --patch)
                BUMP_TYPE="patch"
                shift
                ;;
            --minor)
                BUMP_TYPE="minor"
                shift
                ;;
            --major)
                BUMP_TYPE="major"
                shift
                ;;
            -v|--version)
                if [ -n "${2:-}" ]; then
                    VERSION="$2"
                    shift 2
                else
                    print_error "--version requires a version argument"
                    exit 1
                fi
                ;;
            -m|--message)
                if [ -n "${2:-}" ]; then
                    RELEASE_MESSAGE="$2"
                    shift 2
                else
                    print_error "--message requires a message argument"
                    exit 1
                fi
                ;;
            -w|--watch)
                WATCH_WORKFLOW=true
                shift
                ;;
            --no-push)
                PUSH_TO_REMOTE=false
                shift
                ;;
            --skip-tests|--no-test)
                RUN_TESTS=false
                shift
                ;;
            --allow-dirty)
                ALLOW_DIRTY=true
                shift
                ;;
            --allow-branch)
                ALLOW_BRANCH=true
                shift
                ;;
            -n|--dry-run)
                DRY_RUN=true
                shift
                ;;
            -y|--yes|--non-interactive)
                AUTO_CONFIRM=true
                shift
                ;;
            -*)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
            *)
                if [ -z "$VERSION" ]; then
                    VERSION="$1"
                    shift
                else
                    print_error "Unexpected argument: $1"
                    show_help
                    exit 1
                fi
                ;;
        esac
    done
}

# Extract current version from pyproject.toml
get_current_version() {
    if [ -f "pyproject.toml" ]; then
        grep -E '^version[[:space:]]*=' pyproject.toml | head -n 1 | sed -E 's/^version[[:space:]]*=[[:space:]]*"([^"]+)".*$/\1/'
    elif [ -f "src/tvtv2xmltv/__init__.py" ]; then
        grep -E '^__version__[[:space:]]*=' src/tvtv2xmltv/__init__.py | head -n 1 | sed -E 's/^__version__[[:space:]]*=[[:space:]]*"([^"]+)".*$/\1/'
    else
        echo "1.0.0"
    fi
}

# Extract GitHub repo slug (e.g. AndyG-0/tvtv2xmltv) from git remote
detect_repo_slug() {
    local remote_url
    remote_url=$(git remote get-url origin 2>/dev/null || true)
    if [ -n "$remote_url" ]; then
        local extracted
        extracted=$(echo "$remote_url" | sed -E 's#^.*[:/]([^/]+/[^/]+)(\.git)?$#\1#' | sed 's/\.git$//')
        if [ -n "$extracted" ] && [[ "$extracted" == *"/"* ]]; then
            REPO_SLUG="$extracted"
            return 0
        fi
    fi

    REPO_SLUG="AndyG-0/tvtv2xmltv"
}

# Bump semver version
calculate_bump() {
    local base_ver="$1"
    local bump="$2"
    local major minor patch

    # Strip leading 'v' if present
    base_ver="${base_ver#v}"

    major=$(echo "$base_ver" | cut -d. -f1)
    minor=$(echo "$base_ver" | cut -d. -f2)
    patch=$(echo "$base_ver" | cut -d. -f3 | cut -d- -f1)

    major="${major:-1}"
    minor="${minor:-0}"
    patch="${patch:-0}"

    case "$bump" in
        major)
            echo "$((major + 1)).0.0"
            ;;
        minor)
            echo "${major}.$((minor + 1)).0"
            ;;
        patch)
            echo "${major}.${minor}.$((patch + 1))"
            ;;
        *)
            echo "$base_ver"
            ;;
    esac
}

# Validate semantic version format
validate_version() {
    local ver="$1"
    if [[ ! "$ver" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.-]+)?$ ]]; then
        print_error "Version '$ver' does not match semantic versioning format (e.g., 1.0.0, 1.2.3-rc1)."
        return 1
    fi
    return 0
}

# Update version in files if changed
update_version_files() {
    local new_ver="$1"
    local cur_ver="$2"

    if [ "$new_ver" = "$cur_ver" ]; then
        return 0
    fi

    print_info "Updating version from $cur_ver to $new_ver in project files..."

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would update pyproject.toml and src/tvtv2xmltv/__init__.py to version $new_ver"
        return 0
    fi

    # Update pyproject.toml
    if [ -f "pyproject.toml" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' -E "s/^(version[[:space:]]*=[[:space:]]*)\"[^\"]+\"/\1\"$new_ver\"/" pyproject.toml
        else
            sed -i -E "s/^(version[[:space:]]*=[[:space:]]*)\"[^\"]+\"/\1\"$new_ver\"/" pyproject.toml
        fi
        print_success "Updated pyproject.toml -> $new_ver"
    fi

    # Update src/tvtv2xmltv/__init__.py
    if [ -f "src/tvtv2xmltv/__init__.py" ]; then
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' -E "s/^(__version__[[:space:]]*=[[:space:]]*)\"[^\"]+\"/\1\"$new_ver\"/" src/tvtv2xmltv/__init__.py
        else
            sed -i -E "s/^(__version__[[:space:]]*=[[:space:]]*)\"[^\"]+\"/\1\"$new_ver\"/" src/tvtv2xmltv/__init__.py
        fi
        print_success "Updated src/tvtv2xmltv/__init__.py -> $new_ver"
    fi
}

# Execute or simulate command
exec_cmd() {
    local cmd_str="$*"
    if [ "$DRY_RUN" = true ]; then
        echo -e "${MAGENTA}[DRY-RUN]${NC} $cmd_str"
        return 0
    else
        echo -e "${BLUE}❯${NC} $cmd_str"
        "$@"
    fi
}

main() {
    parse_args "$@"

    print_header
    if [ "$DRY_RUN" = true ]; then
        echo -e "${MAGENTA}${BOLD}⚡ DRY-RUN MODE: No changes will be committed, tagged, or pushed.${NC}"
        echo ""
    fi

    # Stage 1: Validation & Setup
    print_section "Stage 1: Pre-flight Validations"
    detect_repo_slug

    if [ ! -d ".git" ]; then
        print_error "This script must be executed inside a Git repository."
        exit 1
    fi

    local current_version
    current_version=$(get_current_version)
    print_info "Current detected version: ${BOLD}$current_version${NC}"

    # Determine target version
    if [ -n "$BUMP_TYPE" ]; then
        VERSION=$(calculate_bump "$current_version" "$BUMP_TYPE")
        print_info "Calculated $BUMP_TYPE bump: ${BOLD}$VERSION${NC}"
    elif [ -z "$VERSION" ]; then
        VERSION="$current_version"
        print_info "Using target version: ${BOLD}$VERSION${NC}"
    fi

    # Strip leading 'v'
    VERSION="${VERSION#v}"

    if ! validate_version "$VERSION"; then
        exit 1
    fi

    local GIT_TAG_NAME="v${VERSION}"
    if [ -z "$RELEASE_MESSAGE" ]; then
        RELEASE_MESSAGE="Release v${VERSION}"
    fi

    # Check Git branch
    local current_branch
    current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    if [ "$current_branch" != "main" ] && [ "$current_branch" != "master" ] && [ "$ALLOW_BRANCH" = false ]; then
        print_warning "You are on branch '$current_branch' (expected 'main')."
        if [ "$AUTO_CONFIRM" = false ] && [ "$DRY_RUN" = false ]; then
            read -r -p "Do you want to continue releasing from '$current_branch'? [y/N] " confirm_branch
            if [[ ! "$confirm_branch" =~ ^[Yy]$ ]]; then
                print_error "Aborted by user."
                exit 1
            fi
        fi
    else
        print_success "On release branch: $current_branch"
    fi

    # Check for uncommitted changes (excluding version files if we're bumping)
    if ! git diff --quiet || ! git diff --cached --quiet; then
        if [ "$ALLOW_DIRTY" = false ]; then
            print_warning "Git working tree has uncommitted modifications."
            if [ "$AUTO_CONFIRM" = false ] && [ "$DRY_RUN" = false ]; then
                read -r -p "Continue release with uncommitted changes? [y/N] " confirm_dirty
                if [[ ! "$confirm_dirty" =~ ^[Yy]$ ]]; then
                    print_error "Release aborted due to uncommitted changes. Commit or stash them first, or pass --allow-dirty."
                    exit 1
                fi
            fi
        else
            print_warning "Proceeding with uncommitted changes (--allow-dirty)."
        fi
    else
        print_success "Git working tree is clean."
    fi

    # Check if git tag already exists locally or remotely
    if git rev-parse "$GIT_TAG_NAME" >/dev/null 2>&1; then
        print_warning "Git tag '$GIT_TAG_NAME' already exists locally."
        if [ "$AUTO_CONFIRM" = false ] && [ "$DRY_RUN" = false ]; then
            read -r -p "Overwrite existing local tag '$GIT_TAG_NAME'? [y/N] " confirm_tag
            if [[ ! "$confirm_tag" =~ ^[Yy]$ ]]; then
                print_error "Release aborted: tag '$GIT_TAG_NAME' already exists."
                exit 1
            fi
        fi
    fi

    local IMAGE_REGISTRY_PATH="ghcr.io/$(echo "$REPO_SLUG" | tr '[:upper:]' '[:lower:]')"

    # Release Plan Summary
    echo ""
    echo -e "${CYAN}${BOLD}Release Execution Plan:${NC}"
    echo "  • Target Version:        $VERSION"
    echo "  • Git Tag:               $GIT_TAG_NAME"
    echo "  • Target Branch:         $current_branch"
    echo "  • Push to Remote:        $PUSH_TO_REMOTE"
    echo "  • Run Pre-Release Tests: $RUN_TESTS"
    echo "  • Actions Target Image:  $IMAGE_REGISTRY_PATH:$GIT_TAG_NAME"
    echo "  • Actions Target Image:  $IMAGE_REGISTRY_PATH:latest"
    echo ""

    if [ "$AUTO_CONFIRM" = false ] && [ "$DRY_RUN" = false ]; then
        read -r -p "Proceed with creating and pushing release $GIT_TAG_NAME? [y/N] " confirm_all
        if [[ ! "$confirm_all" =~ ^[Yy]$ ]]; then
            print_error "Release cancelled by user."
            exit 0
        fi
    fi

    # Stage 2: Quality Checks & Testing
    if [ "$RUN_TESTS" = true ]; then
        print_section "Stage 2: Pre-Release Quality Checks"
        if [ -f "./run_ci.sh" ]; then
            print_info "Running CI lint and test suite..."
            if [ "$DRY_RUN" = true ]; then
                exec_cmd ./run_ci.sh --lint --test
            else
                if ./run_ci.sh --lint --test; then
                    print_success "All pre-release tests and lint checks passed."
                else
                    print_error "Pre-release tests failed. Please fix before tagging, or pass --skip-tests."
                    exit 1
                fi
            fi
        elif command -v uv &>/dev/null; then
            print_info "Running pytest suite..."
            if [ "$DRY_RUN" = true ]; then
                exec_cmd uv run pytest tests/ -v
            else
                if PYTHONPATH=src uv run pytest tests/ -v; then
                    print_success "Pytest suite passed."
                else
                    print_error "Tests failed. Release aborted."
                    exit 1
                fi
            fi
        fi
    else
        print_info "Skipping pre-release test suite (--skip-tests)."
    fi

    # Stage 3: Version Synchronization & Commit
    if [ "$VERSION" != "$current_version" ]; then
        print_section "Stage 3: Version Synchronization"
        update_version_files "$VERSION" "$current_version"

        if [ "$DRY_RUN" = false ]; then
            if ! git diff --quiet pyproject.toml src/tvtv2xmltv/__init__.py 2>/dev/null; then
                print_info "Committing version bump to git..."
                exec_cmd git add pyproject.toml src/tvtv2xmltv/__init__.py
                exec_cmd git commit -m "chore(release): bump version to $VERSION"
                print_success "Version bump committed."
            fi
        fi
    fi

    # Stage 4: Tag Release
    print_section "Stage 4: Creating Release Tag"
    print_info "Creating annotated Git tag '$GIT_TAG_NAME'..."
    exec_cmd git tag -a -f "$GIT_TAG_NAME" -m "$RELEASE_MESSAGE"
    print_success "Tag '$GIT_TAG_NAME' created."

    # Stage 5: Push to GitHub & Trigger Actions
    if [ "$PUSH_TO_REMOTE" = true ]; then
        print_section "Stage 5: Pushing to GitHub (Triggering Actions)"
        print_info "Pushing branch '$current_branch' and tag '$GIT_TAG_NAME' to origin..."

        exec_cmd git push origin "$current_branch"
        exec_cmd git push origin "$GIT_TAG_NAME"
        print_success "Pushed '$GIT_TAG_NAME' to GitHub."

        # Check if GitHub CLI is available for release management
        if command -v gh &>/dev/null && gh auth status >/dev/null 2>&1; then
            print_info "GitHub CLI (gh) detected and authenticated."

            if [ "$DRY_RUN" = true ]; then
                exec_cmd gh release create "$GIT_TAG_NAME" --generate-notes --title "$RELEASE_MESSAGE"
            else
                # Create GitHub Release if not already existing
                if ! gh release view "$GIT_TAG_NAME" >/dev/null 2>&1; then
                    print_info "Creating GitHub Release with auto-generated release notes..."
                    if gh release create "$GIT_TAG_NAME" --generate-notes --title "$RELEASE_MESSAGE"; then
                        print_success "GitHub Release '$GIT_TAG_NAME' created."
                    fi
                fi
            fi

            # Optionally watch the workflow
            if [ "$WATCH_WORKFLOW" = true ] && [ "$DRY_RUN" = false ]; then
                print_section "Stage 6: Monitoring GitHub Actions Workflow"
                print_info "Waiting for GitHub Actions workflow to start..."
                sleep 4
                print_info "Streaming workflow run..."
                gh run watch || true
            fi
        fi
    else
        print_info "Skipping push to remote (--no-push)."
        print_info "To trigger GitHub Actions manually, push the tag: git push origin $GIT_TAG_NAME"
    fi

    # Summary
    echo ""
    echo -e "${BLUE}${BOLD}======================================================================${NC}"
    echo -e "${GREEN}${BOLD}  🎉 RELEASE $GIT_TAG_NAME INITIATED SUCCESSFULLY!${NC}"
    echo -e "${BLUE}${BOLD}======================================================================${NC}"
    echo ""
    echo "Release Details:"
    echo "  • Version:        $VERSION"
    echo "  • Git Tag:        $GIT_TAG_NAME"
    echo "  • Repository:     https://github.com/$REPO_SLUG"
    echo ""
    if [ "$PUSH_TO_REMOTE" = true ]; then
        echo -e "${CYAN}${BOLD}GitHub Actions Workflow:${NC}"
        echo "  • Actions Run:    https://github.com/$REPO_SLUG/actions"
        echo "  • Container Image Building in Actions:"
        echo "      - $IMAGE_REGISTRY_PATH:$VERSION"
        echo "      - $IMAGE_REGISTRY_PATH:$GIT_TAG_NAME"
        echo "      - $IMAGE_REGISTRY_PATH:latest"
        echo ""
        echo -e "${GREEN}GitHub Actions will automatically build, test, and publish the container image.${NC}"
    else
        echo -e "${YELLOW}Release tag created locally. Run 'git push origin $GIT_TAG_NAME' to trigger GitHub Actions.${NC}"
    fi
    echo ""
}

main "$@"
