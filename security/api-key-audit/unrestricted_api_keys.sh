#!/bin/bash

# Ensure required commands are installed
for cmd in gcloud jq column; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: '$cmd' is required but not installed." >&2
    exit 1
  fi
done

# Temporary files to store intermediate results
TEMP_JSON=$(mktemp)
TEMP_PROJECTS=$(mktemp)
spinner_pid=""

# Cleanup function to stop background processes and remove temp files
cleanup() {
  if [ -n "$spinner_pid" ] && kill -0 "$spinner_pid" 2>/dev/null; then
    kill "$spinner_pid" 2>/dev/null
  fi
  rm -f "$TEMP_JSON" "$TEMP_PROJECTS"
  tput cnorm # Restore cursor visibility
}
trap cleanup EXIT INT TERM

# Background animation spinner function
show_spinner() {
  local delay=0.1
  local spinstr='|/-\'
  tput civis # Hide cursor
  while true; do
    local temp=${spinstr#?}
    printf " [%c] Fetching Google Cloud projects... " "$spinstr"
    local spinstr=$temp${spinstr%"$temp"}
    sleep $delay
    printf "\r"
  done
}

# 1. Fetch the list of project IDs
show_spinner &
spinner_pid=$!

gcloud projects list --format="value(projectId)" > "$TEMP_PROJECTS" 2>/dev/null
gcloud_status=$?

# Stop the spinner
kill "$spinner_pid" 2>/dev/null
wait "$spinner_pid" 2>/dev/null
printf "\r\033[K" # Clear the spinner line
tput cnorm # Restore cursor

if [ "$gcloud_status" -ne 0 ]; then
  echo "Error: 'gcloud projects list' failed." >&2
  echo "Please ensure you are authenticated (run 'gcloud auth login')." >&2
  exit 1
fi

# Load projects into an array
projects=()
while IFS= read -r line; do
  [ -n "$line" ] && projects+=("$line")
done < "$TEMP_PROJECTS"

total_projects=${#projects[@]}
if [ "$total_projects" -eq 0 ]; then
  echo "No projects found."
  exit 0
fi

echo "Found ${total_projects} projects."

# 2. Iterate through each project to find unrestricted keys
current=0
for project in "${projects[@]}"; do
  # Display a non-intrusive progress update on stderr
  printf "\rAuditing keys: %d/%d projects checked (Checking: %s)..." "$current" "$total_projects" "$project" >&2
  current=$((current + 1))
  
  # Fetch keys in JSON format
  keys_json=$(gcloud services api-keys list --project="$project" --format=json 2>/dev/null)
  
  if [ -n "$keys_json" ] && [ "$keys_json" != "[]" ]; then
    # Filter keys where "restrictions" is empty, missing, or contains only empty values
    echo "$keys_json" | jq --arg proj "$project" -c '
      .[] | 
      select(
        .restrictions == null or 
        .restrictions == {} or 
        (.restrictions | to_entries | all(.value == null or .value == [] or .value == {}))
      ) | 
      .project_id = $proj
    ' >> "$TEMP_JSON"
  fi
done

# Clear the progress update line
printf "\r\033[K" >&2

# 3. Sort by creation date and print the final table
if [ -s "$TEMP_JSON" ]; then
  echo -e "DISPLAY NAME\tKEY ID\tPROJECT ID\tCREATION DATE" > "$TEMP_PROJECTS"
  
  # Sort entries chronologically by createTime and format as tab-separated columns
  jq -r -s '
    sort_by(.createTime)[] | 
    "\(.displayName // "Unnamed Key")\t\(.uid)\t\(.project_id)\t\(.createTime)"
  ' "$TEMP_JSON" >> "$TEMP_PROJECTS"
  
  # Print the data in a clean, formatted text table
  column -t -s $'\t' "$TEMP_PROJECTS"
else
  echo "Audit complete: No unrestricted API keys were found."
fi