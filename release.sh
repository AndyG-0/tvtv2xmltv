#!/usr/bin/env bash
# ==============================================================================
# release.sh - Release Automation Script for tvtv2xmltv
# Builds, tags, and pushes container image releases and git tags.
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
    echo -e "${BLUE}${BOLD}  🚀 tvtv2xmltv - Release & Image Publishing Pipeline${NC}"
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

Automates building, tagging, and pushing container images and Git tags.

Arguments:
  VERSION                     Release version (e.g., 1.1.0 or v1.1.0).
                              If omitted, detects current version or prompts.

Version Bump Options:
  --patch                     Bump patch version (e.g. 1.0.0 -> 1.0.1)
  --minor                     Bump minor version (e.g. 1.0.0 -> 1.1.0)
  --major                     Bump major version (e.g. 1.0.0 -> 2.0.0)
  -v, --version <VERSION>     Explicitly specify target release version

Container & Registry Options:
  -r, --registry <REGISTRY>   Container registry (default: ghcr.io, or $REGISTRY)
  -i, --image <IMAGE_NAME>    Image name / repository path (default: AndyG-0/tvtv2xmltv, or $IMAGE_NAME)
  -e, --engine <ENGINE>       Container runtime engine: docker or podman (default: auto-detected)
  --no-latest                 Do not tag or push the ':latest' image tag
  --build-only, --no-image-push
                              Build and tag image locally without pushing to registry

Git Release Options:
  --no-git-tag                Skip creating an annotated git tag
  --no-git-push               Skip pushing git tag to remote origin
  --allow-dirty               Allow release with uncommitted changes in working directory
  --allow-branch              Allow release from branches other than main/master

Quality & Execution Options:
  --skip-tests, --no-test     Skip running pre-release lint and test checks
  -n, --dry-run               Simulate release steps without modifying files, tagging, or pushing
  -y, --yes, --non-interactive
                              Skip all interactive confirmation prompts
  -h, --help                  Display this help message and exit

Examples:
  ./release.sh --dry-run                 # Preview release with current version
  ./release.sh --patch                   # Bump patch (1.0.0 -> 1.0.1), build, tag, and push
  ./release.sh 1.1.0                     # Release version 1.1.0
  ./release.sh 1.1.0 --build-only        # Build and tag image 1.1.0 locally without pushing
  ./release.sh --registry docker.io --image myuser/tvtv2xmltv
EOF
}

# Defaults
VERSION=""
BUMP_TYPE=""
REGISTRY="${REGISTRY:-ghcr.io}"
IMAGE_NAME="${IMAGE_NAME:-}"
CONTAINER_ENGINE="${CONTAINER_ENGINE:-}"
TAG_LATEST=true
PUSH_IMAGE=true
GIT_TAG=true
GIT_PUSH=true
RUN_TESTS=true
ALLOW_DIRTY=false
ALLOW_BRANCH=false
DRY_RUN=false
AUTO_CONFIRM=false

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
            -r|--registry)
                if [ -n "${2:-}" ]; then
                    REGISTRY="$2"
                    shift 2
                else
                    print_error "--registry requires a registry argument"
                    exit 1
                fi
                ;;
            -i|--image)
                if [ -n "${2:-}" ]; then
                    IMAGE_NAME="$2"
                    shift 2
                else
                    print_error "--image requires an image name argument"
                    exit 1
                fi
                ;;
            -e|--engine)
                if [ -n "${2:-}" ]; then
                    CONTAINER_ENGINE="$2"
                    shift 2
                else
                    print_error "--engine requires an engine argument (docker or podman)"
                    exit 1
                fi
                ;;
            --no-latest)
                TAG_LATEST=false
                shift
                ;;
            --build-only|--no-push|--no-image-push)
                PUSH_IMAGE=false
                shift
                ;;
            --no-git-tag)
                GIT_TAG=false
                shift
                ;;
            --no-git-push)
                GIT_PUSH=false
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

# Detect container engine (docker or podman)
detect_container_engine() {
    if [ -n "$CONTAINER_ENGINE" ]; then
        if command -v "$CONTAINER_ENGINE" &>/dev/null; then
            print_success "Using specified container engine: $CONTAINER_ENGINE"
            return 0
        else
            print_error "Specified container engine '$CONTAINER_ENGINE' not found in PATH."
            exit 1
        fi
    fi

    if command -v docker &>/dev/null; then
        CONTAINER_ENGINE="docker"
        print_success "Detected container engine: docker"
    elif command -v podman &>/dev/null; then
        CONTAINER_ENGINE="podman"
        print_success "Detected container engine: podman"
    else
        print_error "Neither 'docker' nor 'podman' was found in PATH."
        print_info "Please install Docker or Podman to build and push container images."
        exit 1
    fi
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

# Extract default repository image name from git remote
detect_image_name() {
    if [ -n "$IMAGE_NAME" ]; then
        return 0
    fi

    local remote_url
    remote_url=$(git remote get-url origin 2>/dev/null || true)
    if [ -n "$remote_url" ]; then
        local extracted
        extracted=$(echo "$remote_url" | sed -E 's#^.*[:/]([^/]+/[^/]+)(\.git)?$#\1#' | tr '[:upper:]' '[:lower:]' | sed 's/\.git$//')
        if [ -n "$extracted" ] && [[ "$extracted" == *"/"* ]]; then
            IMAGE_NAME="$extracted"
            return 0
        fi
    fi

    # Fallback to project name
    IMAGE_NAME="andyg-0/tvtv2xmltv"
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

    # Defaults if missing parts
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
    detect_container_engine
    detect_image_name

    local current_version
    current_version=$(get_current_version)
    print_info "Current detected version: ${BOLD}$current_version${NC}"

    # Determine target version
    if [ -n "$BUMP_TYPE" ]; then
        VERSION=$(calculate_bump "$current_version" "$BUMP_TYPE")
        print_info "Calculated $BUMP_TYPE bump: ${BOLD}$VERSION${NC}"
    elif [ -z "$VERSION" ]; then
        VERSION="$current_version"
        print_info "Using current version: ${BOLD}$VERSION${NC}"
    fi

    # Strip any leading 'v'
    VERSION="${VERSION#v}"

    if ! validate_version "$VERSION"; then
        exit 1
    fi

    local GIT_TAG_NAME="v${VERSION}"
    local MAJOR_VERSION
    local MINOR_VERSION
    MAJOR_VERSION=$(echo "$VERSION" | cut -d. -f1)
    MINOR_VERSION=$(echo "$VERSION" | cut -d. -f2)

    # Check Git repository status
    if [ -d ".git" ]; then
        local current_branch
        current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
        if [ "$current_branch" != "main" ] && [ "$current_branch" != "master" ] && [ "$ALLOW_BRANCH" = false ]; then
            print_warning "You are currently on branch '$current_branch' (expected 'main')."
            if [ "$AUTO_CONFIRM" = false ] && [ "$DRY_RUN" = false ]; then
                read -r -p "Do you want to continue releasing from '$current_branch'? [y/N] " confirm_branch
                if [[ ! "$confirm_branch" =~ ^[Yy]$ ]]; then
                    print_error "Aborted by user."
                    exit 1
                fi
            fi
        else
            print_success "On valid release branch: $current_branch"
        fi

        # Check for uncommitted changes
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

        # Check if git tag already exists
        if git rev-parse "$GIT_TAG_NAME" >/dev/null 2>&1; then
            if [ "$GIT_TAG" = true ]; then
                print_warning "Git tag '$GIT_TAG_NAME' already exists locally."
                if [ "$AUTO_CONFIRM" = false ] && [ "$DRY_RUN" = false ]; then
                    read -r -p "Overwrite existing git tag '$GIT_TAG_NAME'? [y/N] " confirm_tag
                    if [[ ! "$confirm_tag" =~ ^[Yy]$ ]]; then
                        print_info "Skipping git tag creation (--no-git-tag)."
                        GIT_TAG=false
                    fi
                fi
            fi
        fi
    fi

    # Target Registry Image prefix
    local FULL_IMAGE_NAME="${REGISTRY}/${IMAGE_NAME}"
    local LOCAL_IMAGE_NAME="tvtv2xmltv"

    # Image Tags List
    local TARGET_TAGS=()
    TARGET_TAGS+=("${FULL_IMAGE_NAME}:${VERSION}")
    TARGET_TAGS+=("${FULL_IMAGE_NAME}:v${VERSION}")
    TARGET_TAGS+=("${FULL_IMAGE_NAME}:${MAJOR_VERSION}.${MINOR_VERSION}")
    TARGET_TAGS+=("${FULL_IMAGE_NAME}:${MAJOR_VERSION}")
    if [ "$TAG_LATEST" = true ]; then
        TARGET_TAGS+=("${FULL_IMAGE_NAME}:latest")
    fi

    # Release Plan Summary
    echo ""
    echo -e "${CYAN}${BOLD}Release Plan:${NC}"
    echo "  • Version:         $VERSION (Git Tag: $GIT_TAG_NAME)"
    echo "  • Container:       $CONTAINER_ENGINE"
    echo "  • Registry Image:  $FULL_IMAGE_NAME"
    echo "  • Generated Tags:  "
    for tag in "${TARGET_TAGS[@]}"; do
        echo "      - $tag"
    done
    echo "      - ${LOCAL_IMAGE_NAME}:${VERSION} (local)"
    if [ "$TAG_LATEST" = true ]; then
        echo "      - ${LOCAL_IMAGE_NAME}:latest (local)"
    fi
    echo "  • Push Images:     $PUSH_IMAGE"
    echo "  • Create Git Tag:  $GIT_TAG"
    echo "  • Push Git Tag:    $GIT_PUSH"
    echo "  • Run Tests:       $RUN_TESTS"
    echo ""

    if [ "$AUTO_CONFIRM" = false ] && [ "$DRY_RUN" = false ]; then
        read -r -p "Proceed with release $VERSION? [y/N] " confirm_all
        if [[ ! "$confirm_all" =~ ^[Yy]$ ]]; then
            print_error "Release cancelled by user."
            exit 0
        fi
    fi

    # Stage 2: Synchronize version files
    if [ "$VERSION" != "$current_version" ]; then
        print_section "Stage 2: Version Synchronization"
        update_version_files "$VERSION" "$current_version"

        if [ -d ".git" ] && [ "$DRY_RUN" = false ]; then
            if ! git diff --quiet pyproject.toml src/tvtv2xmltv/__init__.py 2>/dev/null; then
                print_info "Committing version bump to git..."
                exec_cmd git add pyproject.toml src/tvtv2xmltv/__init__.py
                exec_cmd git commit -m "chore(release): bump version to $VERSION"
                print_success "Version bump committed."
            fi
        fi
    fi

    # Stage 3: Quality Checks & Testing
    if [ "$RUN_TESTS" = true ]; then
        print_section "Stage 3: Pre-Release Quality Checks"
        if [ -f "./run_ci.sh" ]; then
            print_info "Running CI lint and test suite..."
            if [ "$DRY_RUN" = true ]; then
                exec_cmd ./run_ci.sh --lint --test
            else
                if ./run_ci.sh --lint --test; then
                    print_success "All pre-release tests and lint checks passed."
                else
                    print_error "Pre-release tests failed. Resolve issues or run with --skip-tests."
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

    # Stage 4: Build Container Image
    print_section "Stage 4: Building Container Image"
    print_info "Building base image '${LOCAL_IMAGE_NAME}:${VERSION}' with $CONTAINER_ENGINE..."
    exec_cmd "$CONTAINER_ENGINE" build -t "${LOCAL_IMAGE_NAME}:${VERSION}" .

    # Smoke test built image
    print_info "Running smoke test on built container image..."
    if [ "$DRY_RUN" = false ]; then
        local smoke_output
        if smoke_output=$("$CONTAINER_ENGINE" run --rm "${LOCAL_IMAGE_NAME}:${VERSION}" python -c "import tvtv2xmltv; print(tvtv2xmltv.__version__)" 2>&1); then
            print_success "Container smoke test passed (version: $smoke_output)."
        else
            print_error "Container smoke test failed: $smoke_output"
            exit 1
        fi
    else
        exec_cmd "$CONTAINER_ENGINE" run --rm "${LOCAL_IMAGE_NAME}:${VERSION}" python -c "import tvtv2xmltv; print(tvtv2xmltv.__version__)"
    fi

    # Stage 5: Tag Image Variants
    print_section "Stage 5: Tagging Container Images"
    if [ "$TAG_LATEST" = true ]; then
        exec_cmd "$CONTAINER_ENGINE" tag "${LOCAL_IMAGE_NAME}:${VERSION}" "${LOCAL_IMAGE_NAME}:latest"
        print_success "Tagged ${LOCAL_IMAGE_NAME}:latest"
    fi

    for tag in "${TARGET_TAGS[@]}"; do
        exec_cmd "$CONTAINER_ENGINE" tag "${LOCAL_IMAGE_NAME}:${VERSION}" "$tag"
        print_success "Tagged $tag"
    done

    # Stage 6: Push Container Images
    if [ "$PUSH_IMAGE" = true ]; then
        print_section "Stage 6: Pushing Container Images to Registry ($REGISTRY)"
        for tag in "${TARGET_TAGS[@]}"; do
            print_info "Pushing $tag..."
            if ! exec_cmd "$CONTAINER_ENGINE" push "$tag"; then
                print_error "Failed to push $tag."
                print_warning "Ensure you are authenticated to $REGISTRY (e.g., 'docker login $REGISTRY' or 'podman login $REGISTRY')."
                exit 1
            fi
            print_success "Pushed $tag"
        done
    else
        print_info "Skipping container image push (--build-only / --no-image-push)."
    fi

    # Stage 7: Git Tag & Push
    if [ -d ".git" ]; then
        if [ "$GIT_TAG" = true ]; then
            print_section "Stage 7: Git Release Tagging"
            print_info "Creating annotated git tag '$GIT_TAG_NAME'..."
            exec_cmd git tag -a -f "$GIT_TAG_NAME" -m "Release $GIT_TAG_NAME"
            print_success "Created git tag '$GIT_TAG_NAME'."

            if [ "$GIT_PUSH" = true ]; then
                print_info "Pushing git tag '$GIT_TAG_NAME' to origin..."
                exec_cmd git push origin "$GIT_TAG_NAME"
                print_success "Pushed git tag '$GIT_TAG_NAME' to origin."
            else
                print_info "Skipping git push (--no-git-push). To push manually: git push origin $GIT_TAG_NAME"
            fi
        else
            print_info "Skipping git tagging (--no-git-tag)."
        fi
    fi

    # Summary
    echo ""
    echo -e "${BLUE}${BOLD}======================================================================${NC}"
    echo -e "${GREEN}${BOLD}  🎉 RELEASE v${VERSION} COMPLETED SUCCESSFULLY!${NC}"
    echo -e "${BLUE}${BOLD}======================================================================${NC}"
    echo ""
    echo "Summary of release artifacts:"
    echo "  • Version:        $VERSION"
    if [ "$GIT_TAG" = true ]; then
        echo "  • Git Tag:        $GIT_TAG_NAME"
    fi
    echo "  • Container Tags:"
    for tag in "${TARGET_TAGS[@]}"; do
        echo "      - $tag"
    done
    echo ""
    if [ "$PUSH_IMAGE" = true ]; then
        echo -e "${GREEN}Container images have been published to ${REGISTRY}/${IMAGE_NAME}!${NC}"
    else
        echo -e "${YELLOW}Images were built and tagged locally. Run without --build-only to push.${NC}"
    fi
    echo ""
}

main "$@"
