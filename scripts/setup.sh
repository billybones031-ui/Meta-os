#!/usr/bin/env bash
# Meta-OS v3.2 — One-shot Oracle ARM64 / Debian setup
# Run as non-root user with sudo.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "=== [1/6] System packages ==="
sudo apt-get update -qq
sudo apt-get install -y --no-install-recommends \
    curl wget git tmux build-essential \
    python3 python3-pip python3-venv \
    golang-go ufw

echo "=== [2/6] Firewall ==="
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 5678/tcp  # n8n
sudo ufw allow 11434/tcp # Ollama
sudo ufw --force enable

echo "=== [3/6] Ollama ==="
if ! command -v ollama &>/dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi
sudo systemctl enable --now ollama || true
echo "Pulling models in background..."
ollama pull llama3.2:3b   &
ollama pull nomic-embed-text &
echo "(gemma3:4b and mistral:7b can be pulled manually when bandwidth allows)"

echo "=== [4/6] Node / n8n ==="
if ! command -v node &>/dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi
if ! command -v n8n &>/dev/null; then
    sudo npm install -g n8n --build-from-source
fi

echo "=== [5/6] Python deps ==="
cd "$REPO_DIR"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "=== [6/6] Go observer ==="
cd "$REPO_DIR/observer"
go build -o observer_bin main.go
echo "Observer built: $REPO_DIR/observer/observer_bin"

echo ""
echo "Setup complete. Edit .env, then run: bash scripts/start_all.sh"
