#!/bin/bash
# Check if the "wplocalvolumen" folder exists (if not, create it)
if [ ! -d "wplocalvolumen" ]; then
  mkdir wplocalvolumen
fi

docker-compose up