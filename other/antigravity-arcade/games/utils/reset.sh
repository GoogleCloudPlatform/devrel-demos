#!/bin/bash

# ==============================================================================
# Purpose: Resets the workspace by deleting modified game files and restoring
# them from a read-only backup in the user's Documents folder. Allows resetting
# all games or a specific target game passed as an argument.
#
# Trade-offs and Decisions:
# - Excludes system folders like node_modules and utils from deletion to preserve
# dependencies and tooling.
# - Accepts an optional argument to target a single game for reset, minimizing
# I/O overhead and preserving WIP in other games when only one game needs restoring.
# - Runs as the developer user (demouser) without sudo to ensure correct file ownership.
# - Assumes backup exists in <workspace>/utils/backup
# ==============================================================================
#
# @file reset.sh
# @brief Resets the game workspace to default state.
# @param $1 Optional game name to reset a single game (e.g., space-shooter). If omitted, resets all games.
#
# This script:
# 1. Checks if a specific game argument is provided.
# 2. Iterates through items in /opt/AntigravityArcade (or targets the specific game).
# 3. Deletes items that are not in the exclusion list (or deletes the specific game).
# 4. Copies game folders from backup to the workspace.
#

# Terminate execution immediately upon any command failure to prevent partial/corrupted workspace resets
set -e

# Establish absolute directory paths to reliably locate backup assets regardless of caller working directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
BACKUP_DIR="$SCRIPT_DIR/backup"
TARGET_GAME="$1"

if [ -n "$TARGET_GAME" ]; then
    echo "Resetting game '$TARGET_GAME' in $WORKSPACE_DIR..."
    # Validate requested game against available backups to prevent wiping a directory without a restoration source
    if [ ! -d "$BACKUP_DIR/$TARGET_GAME" ]; then
        echo "Error: Backup for game '$TARGET_GAME' does not exist in $BACKUP_DIR."
        exit 1
    fi
else
    echo "Resetting all games in $WORKSPACE_DIR..."
fi

# 1. Delete existing game folders in workspace.
# We do this manually because demouser has permission to delete files they don't own
# (due to write access on the parent directory), but rsync would fail to update them in place
# if they are read-only.
echo "Deleting existing game folders..."
if [ -n "$TARGET_GAME" ]; then
    # Isolate deletion to the targeted game to avoid disrupting unassociated project directories
    if [ -e "$WORKSPACE_DIR/$TARGET_GAME" ]; then
        echo "Removing: $TARGET_GAME"
        rm -rf "$WORKSPACE_DIR/$TARGET_GAME"
    fi
else
    # Traverse workspace directory to identify and purge all modified game directories
    for item in "$WORKSPACE_DIR"/*; do
        [ -e "$item" ] || continue
        basename=$(basename "$item")
        case "$basename" in
            ".agents"|"node_modules"|"game-template"|"utils"|"package.json"|"package-lock.json")
                # Preserve system infrastructure and dependency configurations required for runtime stability
                ;;
            *)
                echo "Removing: $basename"
                rm -rf "$item"
                ;;
        esac
    done
fi

# 2. Restore from backup.
# We use -rlv to avoid preserving strict permissions/times from the backup,
# allowing the new files to be owned and editable by the demouser.
echo "Restoring game folders from $BACKUP_DIR..."
if [ -d "$BACKUP_DIR" ]; then
    if [ -n "$TARGET_GAME" ]; then
        # Selectively synchronize only the requested game directory to optimize restore time
        rsync -rlv "$BACKUP_DIR/$TARGET_GAME" "$WORKSPACE_DIR/"
        
        # 3. Ensure game folders are writable by the group (developers)
        # Grant group write access to allow subsequent modifications by developer accounts in shared environments
        echo "Setting write permissions for group on $TARGET_GAME..."
        chmod -R g+w "$WORKSPACE_DIR/$TARGET_GAME"
    else
        # Bulk synchronize the entire backup repository to achieve a complete workspace baseline reset
        rsync -rlv "$BACKUP_DIR/" "$WORKSPACE_DIR/"
        
        # 3. Ensure game folders are writable by the group (developers)
        # Grant group write access to allow subsequent modifications by developer accounts in shared environments
        echo "Setting write permissions for group..."
        for dir in "$BACKUP_DIR"/*; do
            [ -d "$dir" ] || continue
            basename=$(basename "$dir")
            echo "Making $basename writable by group..."
            chmod -R g+w "$WORKSPACE_DIR/$basename"
        done
    fi
else
    echo "Error: Backup directory $BACKUP_DIR does not exist."
    exit 1
fi

echo "Workspace reset complete!"
