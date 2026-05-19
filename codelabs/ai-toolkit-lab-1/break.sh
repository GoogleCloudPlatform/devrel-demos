#!/bin/bash
# This script introduces bugs into the active manifests for the lab.

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}💥 Breaking manifests...${NC}"
cp manifests-broken/*.yaml cymbal-bank/kubernetes-manifests/
echo -e "${RED}😈 Manifests broken. ${GREEN}Ready for the lab challenge!${NC}"
