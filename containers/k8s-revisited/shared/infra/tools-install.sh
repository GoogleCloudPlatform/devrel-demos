#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Install kind, kubectl, helm, kwok, kwokctl and kubeconform into ~/.local/bin.
#
# Versions come from the environment (KIND_VERSION, KUBECTL_VERSION, HELM_VERSION,
# KWOK_VERSION, KUBECONFORM_VERSION). Unset versions resolve to the latest release
# (kubectl: the latest 1.37 patch). Downloads are checked against the published
# SHA-256 where one exists; every installed binary is recorded in tools.lock.
#
# Usage: tools-install.sh [--dry-run]
set -euo pipefail

BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
LOCK="${LOCK:-$(cd "$(dirname "$0")" && pwd)/tools.lock}"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

case "$(uname -s)" in Linux) OS=linux ;; Darwin) OS=darwin ;; *) echo "unsupported OS" >&2; exit 1 ;; esac
case "$(uname -m)" in x86_64|amd64) ARCH=amd64 ;; aarch64|arm64) ARCH=arm64 ;; *) echo "unsupported arch" >&2; exit 1 ;; esac

latest_github() {
  curl -fsSL "https://api.github.com/repos/$1/releases/latest" |
    python3 -c 'import json,sys; print(json.load(sys.stdin)["tag_name"])'
}

KUBECTL_VERSION="${KUBECTL_VERSION:-$(curl -fsSL https://dl.k8s.io/release/stable-1.37.txt)}"
KIND_VERSION="${KIND_VERSION:-$(latest_github kubernetes-sigs/kind)}"
HELM_VERSION="${HELM_VERSION:-$(latest_github helm/helm)}"
KWOK_VERSION="${KWOK_VERSION:-$(latest_github kubernetes-sigs/kwok)}"
KUBECONFORM_VERSION="${KUBECONFORM_VERSION:-$(latest_github yannh/kubeconform)}"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$BIN_DIR"
: > "$TMP/lock"

sha_of() { sha256sum "$1" | awk '{print $1}'; }

# fetch NAME URL CHECKSUM_URL [ENTRY]: downloads URL to $TMP/NAME and checks it.
# CHECKSUM_URL may hold a bare hash or "hash  filename" lines; ENTRY picks the line.
fetch() {
  local name="$1" url="$2" sum_url="${3:-}" entry="${4:-}"
  echo "fetch $url"
  if [ "$DRY" = "1" ]; then return 0; fi
  curl -fsSL -o "$TMP/$name" "$url"
  local got want=""
  got="$(sha_of "$TMP/$name")"
  if [ -n "$sum_url" ]; then
    if [ -n "$entry" ]; then
      want="$(curl -fsSL "$sum_url" | awk -v e="$entry" '$2 == e || $2 == "*"e {print $1}' | head -n1)"
    else
      want="$(curl -fsSL "$sum_url" | awk '{print $1}' | head -n1)"
    fi
    [ -n "$want" ] || { echo "no checksum entry for $name" >&2; exit 1; }
    [ "$got" = "$want" ] || { echo "checksum mismatch for $name: $got != $want" >&2; exit 1; }
    echo "  sha256 ok ($got)"
  else
    echo "  no published checksum; recording $got"
  fi
  printf '%s %s\n' "$url" "$got" >> "$TMP/lock"
}

install_bin() {
  [ "$DRY" = "1" ] && return 0
  install -m 0755 "$1" "$BIN_DIR/$2"
  echo "  installed $BIN_DIR/$2"
}

# kubectl
fetch kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/${OS}/${ARCH}/kubectl" \
  "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/${OS}/${ARCH}/kubectl.sha256"
install_bin "$TMP/kubectl" kubectl

# kind
fetch kind "https://github.com/kubernetes-sigs/kind/releases/download/${KIND_VERSION}/kind-${OS}-${ARCH}" \
  "https://github.com/kubernetes-sigs/kind/releases/download/${KIND_VERSION}/kind-${OS}-${ARCH}.sha256sum" "kind-${OS}-${ARCH}"
install_bin "$TMP/kind" kind

# helm
fetch helm.tgz "https://get.helm.sh/helm-${HELM_VERSION}-${OS}-${ARCH}.tar.gz" \
  "https://get.helm.sh/helm-${HELM_VERSION}-${OS}-${ARCH}.tar.gz.sha256sum" "helm-${HELM_VERSION}-${OS}-${ARCH}.tar.gz"
if [ "$DRY" != "1" ]; then tar -xzf "$TMP/helm.tgz" -C "$TMP"; fi
install_bin "$TMP/${OS}-${ARCH}/helm" helm

# kwok and kwokctl
for b in kwok kwokctl; do
  fetch "$b" "https://github.com/kubernetes-sigs/kwok/releases/download/${KWOK_VERSION}/${b}-${OS}-${ARCH}"
  install_bin "$TMP/$b" "$b"
done

# kubeconform
fetch kubeconform.tgz "https://github.com/yannh/kubeconform/releases/download/${KUBECONFORM_VERSION}/kubeconform-${OS}-${ARCH}.tar.gz" \
  "https://github.com/yannh/kubeconform/releases/download/${KUBECONFORM_VERSION}/CHECKSUMS" "kubeconform-${OS}-${ARCH}.tar.gz"
if [ "$DRY" != "1" ]; then tar -xzf "$TMP/kubeconform.tgz" -C "$TMP" kubeconform; fi
install_bin "$TMP/kubeconform" kubeconform

if [ "$DRY" != "1" ]; then
  {
    echo "# Written by tools-install.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ) for ${OS}/${ARCH}"
    echo "# kubectl=${KUBECTL_VERSION} kind=${KIND_VERSION} helm=${HELM_VERSION} kwok=${KWOK_VERSION} kubeconform=${KUBECONFORM_VERSION}"
    cat "$TMP/lock"
  } > "$LOCK"
  echo "wrote $LOCK"
  case ":$PATH:" in *":$BIN_DIR:"*) ;; *) echo "note: add $BIN_DIR to your PATH" ;; esac
fi
