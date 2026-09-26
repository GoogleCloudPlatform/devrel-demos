#!/bin/bash
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# One-command Antigravity CLI setup for Cloud Shell. Configures agy, then
# launches it interactively in the current terminal.
#
# Recommended (AGY_ADC_AUTH stays set in the current shell after agy exits):
#   source <(curl -fsSL <RAW_URL>)
#
# Also supported (agy runs, but the current shell only gets AGY_ADC_AUTH
# after `source ~/.bashrc` or in a new terminal):
#   curl -fsSL <RAW_URL> | bash
#   bash <(curl -fsSL <RAW_URL>)
#
# This file may be sourced into the user's interactive shell, so it must never
# call `exit` or enable `set -e`: either would close the user's terminal.

__agy_lab_setup() {
  local agy_dir="$HOME/.gemini/antigravity-cli"

  mkdir -p "$agy_dir/cache" || return 1

  # Idempotent: re-running the command must not duplicate the line.
  if ! grep -qxF 'export AGY_ADC_AUTH=true' "$HOME/.bashrc" 2>/dev/null; then
    echo 'export AGY_ADC_AUTH=true' >> "$HOME/.bashrc" || return 1
  fi
  # Inherited by agy below, and by the current shell when sourced.
  export AGY_ADC_AUTH=true

  # Unquoted delimiter on purpose: identical to the lab instructions, so
  # $HOME expands to the user's home directory.
  cat << EOF > "$agy_dir/settings.json" || return 1
{
  "model": "Gemini 3.7 Flash (Medium)",
  "trustedWorkspaces": [
    "~",
    "$HOME"
  ],
  "colorScheme": "dark",
  "enableTelemetry": true,
  "altScreenMode": "default",
  "notifications": false,
  "showTips": false,
  "showFeedbackSurvey": false,
  "editor": "auto",
  "editorMode": "default",
  "vimInsertFirst": false,
  "allowNonWorkspaceAccess": false,
  "enableTerminalSandbox": false,
  "agentMode": "accept-edits",
  "permissions": {
    "allow": [
      "command(regex:^ls\\b.*)",
      "command(regex:^cat\\b.*)",
      "command(regex:^grep\\b.*)",
      "command(regex:^rg\\b.*)",
      "command(regex:^find\\b.*)",
      "command(regex:^head\\b.*)",
      "command(regex:^tail\\b.*)",
      "command(regex:^less\\b.*)",
      "command(regex:^tree\\b.*)",
      "command(regex:^pwd\\b.*)",
      "command(regex:^echo\\b.*)",
      "command(regex:^which\\b.*)",
      "command(regex:^date\\b.*)",
      "command(regex:^whoami\\b.*)",
      "command(regex:^git status.*)",
      "command(regex:^git log.*)",
      "command(regex:^git diff.*)",
      "command(regex:^git show.*)",
      "command(regex:^git branch.*)",
      "command(regex:^git fetch.*)",
      "command(regex:^git remote.*)",
      "command(regex:^git grep.*)",
      "command(regex:^git --version.*)"
    ]
  }
}
EOF

  cat << 'EOF' > "$agy_dir/cache/onboarding.json" || return 1
{
  "consumerOnboardingComplete": true,
  "enterpriseOnboardingComplete": true,
  "onboardingComplete": true
}
EOF

  # Cloud Shell ships agy in /usr/bin. Fall back to the official installer
  # (default target: ~/.local/bin) if it is ever missing.
  if ! command -v agy > /dev/null 2>&1; then
    curl -fsSL https://antigravity.google/cli/install.sh | bash || return 1
    export PATH="$HOME/.local/bin:$PATH"
    command -v agy > /dev/null 2>&1 || return 1
  fi
}

echo -e "\n\nConfiguring Antigravity CLI...\n\n"

if __agy_lab_setup; then
  unset -f __agy_lab_setup
  # `return` succeeds at the top level only when this file is sourced.
  if (return 0 2> /dev/null); then
    # Sourced: run agy in the foreground of the user's shell. Using exec here
    # would replace the shell and close the terminal when agy exits.
    agy
  else
    # Executed. With `curl | bash`, stdin is the pipe that carries this
    # script, so reattach agy's stdin to the terminal to make it interactive.
    # exec replaces this script's process: when agy exits, the user is back
    # at their own shell prompt.
    exec agy < /dev/tty
  fi
else
  unset -f __agy_lab_setup
  echo "Antigravity CLI setup failed. See the messages above." >&2
fi
