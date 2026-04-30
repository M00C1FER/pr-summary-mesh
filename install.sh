#!/usr/bin/env bash
# pr-summary-mesh — interactive install wizard with shared CLI registry config.
set -euo pipefail

if [ -t 1 ]; then C_BOLD="$(tput bold)"; C_RESET="$(tput sgr0)"; C_GREEN="$(tput setaf 2)"; C_YELLOW="$(tput setaf 3)"; C_RED="$(tput setaf 1)"; else C_BOLD=""; C_RESET=""; C_GREEN=""; C_YELLOW=""; C_RED=""; fi
say()  { printf "%s%s%s\n" "$C_BOLD" "$1" "$C_RESET"; }
info() { printf "  %s\n" "$1"; }
ok()   { printf "  %s✓%s %s\n" "$C_GREEN" "$C_RESET" "$1"; }
warn() { printf "  %s!%s %s\n" "$C_YELLOW" "$C_RESET" "$1"; }
fail() { printf "  %s✗%s %s\n" "$C_RED" "$C_RESET" "$1" >&2; exit 1; }
prompt_yn() { local q="$1" def="${2:-y}" ans; if [ "$def" = "y" ]; then read -r -p "  $q [Y/n]: " ans; ans="${ans:-y}"; else read -r -p "  $q [y/N]: " ans; ans="${ans:-n}"; fi; [[ "$ans" =~ ^[Yy] ]]; }
prompt_default() { read -r -p "  $1 [$2]: " ans; echo "${ans:-$2}"; }

detect_os() { OS_ID=unknown; OS_LIKE=""; OS_VERSION=""; OS_WSL=0; [ -f /etc/os-release ] && { . /etc/os-release; OS_ID="${ID:-}"; OS_LIKE="${ID_LIKE:-}"; OS_VERSION="${VERSION_ID:-}"; }; [ "$(uname)" = "Darwin" ] && OS_ID=macos; grep -qi microsoft /proc/sys/kernel/osrelease 2>/dev/null && OS_WSL=1 || true; }
pkg_install() {
    case "$OS_ID" in
        debian|ubuntu) sudo apt-get update -qq && sudo apt-get install -y "$@";;
        fedora|rhel|centos) sudo dnf install -y "$@";;
        arch|manjaro) sudo pacman -S --noconfirm "$@";;
        alpine) sudo apk add --no-cache "$@";;
        opensuse*|sles) sudo zypper install -y "$@";;
        macos) brew install "$@";;
        *) warn "unknown OS — install manually: $*"; return 1;;
    esac
}
ensure_python() {
    command -v python3 >/dev/null && {
        local pyv; pyv="$(python3 -c 'import sys; print("%d.%d"%sys.version_info[:2])')"
        case "$pyv" in 3.1[0-9]|3.[2-9][0-9]) ok "Python $pyv"; return 0;; esac
    }
    if prompt_yn "Install Python 3.10+ via system package manager?"; then
        case "$OS_ID" in
            debian|ubuntu) pkg_install python3 python3-venv python3-pip;;
            fedora|rhel|centos) pkg_install python3 python3-pip;;
            arch|manjaro) pkg_install python python-pip;;
            alpine) pkg_install python3 py3-pip;;
            macos) pkg_install python@3.12;;
            *) fail "install Python 3.10+ manually then re-run";;
        esac
    else fail "Python 3.10+ required"; fi
}

main() {
    say "pr-summary-mesh — install wizard"
    detect_os
    info "OS: ${OS_ID}${OS_VERSION:+ $OS_VERSION}$([ "$OS_WSL" = 1 ] && echo ' (WSL2)')"

    say ""; say "Step 1/3: Python 3.10+"; ensure_python

    say ""; say "Step 2/3: Install"
    local INSTALL_HOME; INSTALL_HOME="$(prompt_default "Install root" "$HOME/.local/share/pr-summary-mesh")"
    mkdir -p "$INSTALL_HOME"
    if [ -d "$INSTALL_HOME/.git" ]; then ( cd "$INSTALL_HOME" && git pull -q ); else git clone -q https://github.com/M00C1FER/pr-summary-mesh.git "$INSTALL_HOME"; fi
    cd "$INSTALL_HOME"
    python3 -m venv .venv
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -e .[dev]
    local BIN="${HOME}/.local/bin"; mkdir -p "$BIN"
    cat > "$BIN/pr-summary-mesh" <<EOF
#!/usr/bin/env bash
exec "$INSTALL_HOME/.venv/bin/pr-summary-mesh" "\$@"
EOF
    chmod +x "$BIN/pr-summary-mesh"
    ok "installed"

    say ""; say "Step 3/3: Configure summarizer registry (or reuse triple-review's)"
    info "pr-summary-mesh and triple-review share the same YAML schema."
    local existing="$HOME/.config/triple-review/triple-review.yaml"
    if [ -f "$existing" ] && prompt_yn "Reuse $existing as your summarizer registry?" y; then
        local CFG_DIR="$HOME/.config/pr-summary-mesh"
        mkdir -p "$CFG_DIR"
        ln -sf "$existing" "$CFG_DIR/pr-summary.yaml"
        ok "linked $CFG_DIR/pr-summary.yaml → $existing"
    else
        warn "no shared config — pr-summary-mesh will use the bundled preset (claude/gemini/copilot)."
        info "Run 'pr-summary-mesh --list-clis --diff-file /dev/null' to inspect."
    fi

    say ""
    ok "Done. Try: pr-summary-mesh --pr owner/repo#42 --mode merge"
}
main "$@"
