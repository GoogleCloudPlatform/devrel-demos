#!/bin/bash
echo "Creating Session"
SESSION_RESP=$(curl -s -X POST -H "Content-Type: application/json" -d '{}' http://localhost:8080/api/apps/fitting%20room/users/flutter_user/sessions)
echo $SESSION_RESP
SESSION_ID=$(echo $SESSION_RESP | grep -o '"id":"[^"]*' | cut -d'"' -f4)
echo "Session ID: $SESSION_ID"

if [ -z "$SESSION_ID" ]; then
  echo "Failed to get session ID"
  exit 1
fi

echo "Running Agent"
curl -s -X POST -H "Content-Type: application/json" -d '{
  "appName": "fitting room",
  "userId": "flutter_user",
  "sessionId": "'"$SESSION_ID"'",
  "newMessage": {
    "role": "user",
    "parts": [
      {
        "text": "Generate a virtual try-on. The first image is my photo, the second is the clothing item I want to try on."
      }
    ]
  }
}' http://localhost:8080/api/run
