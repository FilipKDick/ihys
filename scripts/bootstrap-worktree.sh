#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
common_git_dir="$(git -C "$repo_root" rev-parse --git-common-dir)"

case "$common_git_dir" in
  /*) ;;
  *) common_git_dir="$repo_root/$common_git_dir" ;;
esac

main_root="$(dirname "$common_git_dir")"
worktree_name="$(basename "$repo_root" | tr -c '[:alnum:]' '_' | sed 's/_$//')"

checksum="$(printf '%s' "$repo_root" | cksum | cut -d ' ' -f 1)"
postgres_port="$((15432 + checksum % 1000))"
backend_port="$((18000 + checksum % 1000))"
frontend_port="$((13000 + checksum % 1000))"

link_env_file() {
  local file="$1"
  local source="$main_root/$file"
  local target="$repo_root/$file"

  if [[ ! -e "$source" ]]; then
    return
  fi

  if [[ -L "$target" && "$(readlink "$target")" == "$source" ]]; then
    return
  fi

  if [[ -e "$target" || -L "$target" ]]; then
    echo "Leaving existing $target unchanged"
    return
  fi

  ln -s "$source" "$target"
}

link_env_file .env
link_env_file .env.backend
link_env_file .env.frontend
link_env_file .env.db

cat > "$repo_root/compose.override.yml" <<EOF
name: ihys_${worktree_name}

services:
  postgres:
    container_name: ihys_${worktree_name}_postgres
    ports: !override
      - "127.0.0.1:\${IHYS_POSTGRES_PORT:-$postgres_port}:5432"

  backend:
    container_name: ihys_${worktree_name}_backend
    ports: !override
      - "127.0.0.1:\${IHYS_BACKEND_PORT:-$backend_port}:8000"

  frontend:
    container_name: ihys_${worktree_name}_frontend
    ports: !override
      - "127.0.0.1:\${IHYS_FRONTEND_PORT:-$frontend_port}:3000"

  caddy:
    container_name: ihys_${worktree_name}_caddy
    profiles:
      - caddy
EOF

cat <<EOF
Worktree bootstrapped at $repo_root
Main checkout: $main_root
Compose override: $repo_root/compose.override.yml
Ports:
  postgres: ${postgres_port}
  backend: ${backend_port}
  frontend: ${frontend_port}
EOF
