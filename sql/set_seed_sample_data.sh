#!/bin/bash
# sql/set_seed_sample_data.sh
# This script creates a file to indicate whether sample data should be seeded

if [ "$SEED_SAMPLE_DATA" = "true" ]; then
    echo "Seeding sample data"
    touch /tmp/seed_sample_data
else
    echo "Skipping sample data seeding"
fi
