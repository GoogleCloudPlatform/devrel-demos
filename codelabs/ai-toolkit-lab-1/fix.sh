#!/bin/bash
# This script restores the working manifests.

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛠️ Restoring manifests...${NC}"
cp manifests-fixed/*.yaml cymbal-bank/kubernetes-manifests/
echo -e "${GREEN}🎉 Manifests restored to working state!${NC}"
