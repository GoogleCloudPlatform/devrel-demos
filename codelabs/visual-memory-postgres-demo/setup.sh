#!/bin/bash

# Configuration Variables
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"
INSTANCE_NAME="living-memory-db"
DB_NAME="living_memory"
DB_USER="memory_app"
DB_PASS="memory_app_password" 

echo "🚀 Starting setup for Living Memory Database in project: $PROJECT_ID"

# 1. Enable necessary Google Cloud APIs
echo "Enabling Cloud SQL Admin API..."
gcloud services enable sqladmin.googleapis.com

# 2. Create Cloud SQL PostgreSQL instance
echo "Creating Cloud SQL PostgreSQL instance ($INSTANCE_NAME)..."
echo "This step usually takes 5-10 minutes."
gcloud sql instances create $INSTANCE_NAME \
    --database-version=POSTGRES_16 \
    --cpu=1 \
    --memory=3840MB \
    --region=$REGION \
    --root-password=$DB_PASS \
    --edition=ENTERPRISE

# 3. Create the Database
echo "Creating database ($DB_NAME)..."
gcloud sql databases create $DB_NAME --instance=$INSTANCE_NAME

# 4. Create the Application User
echo "Creating database user ($DB_USER)..."
gcloud sql users create $DB_USER --instance=$INSTANCE_NAME --password=$DB_PASS

# 5. Initialize the Schema

# 5.1 Get the Cloud SQL Instance Public IP
INSTANCE_IP=$(gcloud sql instances describe $INSTANCE_NAME --format='value(ipAddresses[0].ipAddress)')

# 5.2 Authorize Cloud Shell or local machine IP
AUTHORIZED_IP=$DEVSHELL_IP_ADDRESS
if [ -z "$AUTHORIZED_IP" ]; then
    echo "DEVSHELL_IP_ADDRESS is not defined. Attempting to fetch public IP..."
    AUTHORIZED_IP=$(curl -s https://api.ipify.org)
    if [ -z "$AUTHORIZED_IP" ]; then
        AUTHORIZED_IP=$(curl -s ifconfig.me)
    fi
    if [ -z "$AUTHORIZED_IP" ]; then
        echo "❌ Could not determine public IP address. Please check your internet connection or use Cloud Shell."
        exit 1
    fi
    echo "🌐 Using fetched public IP: $AUTHORIZED_IP"
else
    echo "🔐 Using Cloud Shell IP: $AUTHORIZED_IP"
fi

echo "🔐 Authorizing IP ($AUTHORIZED_IP)..."
gcloud sql instances patch $INSTANCE_NAME --authorized-networks=$AUTHORIZED_IP --quiet

# 5.3 Import the Schema
# psql uses the exported PGPASSWORD to skip the interactive prompt
echo "📥 Importing schema.sql into $DB_NAME..."
export PGPASSWORD=$DB_PASS
psql -h $INSTANCE_IP -U $DB_USER -d $DB_NAME < schema.sql

# 5.4 Verification
echo "📊 Verification: Tables created in $DB_NAME:"
psql -h $INSTANCE_IP -U $DB_USER -d $DB_NAME -c "\dt"

echo "✅ Setup Complete!"
echo "Your Cloud SQL instance is ready."
echo "Connection string details (for your app config):"
echo "Host: psql (via Cloud SQL Auth Proxy)"
echo "User: $DB_USER"
echo "Database: $DB_NAME"