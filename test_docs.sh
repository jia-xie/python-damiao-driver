#!/bin/bash
# Test script for MkDocs documentation

set -e

echo "Testing MkDocs documentation setup..."
echo ""

# Check if we're in the right directory
if [ ! -f "mkdocs.yml" ]; then
    echo "Error: mkdocs.yml not found. Please run this script from the project root."
    exit 1
fi

# Install documentation dependencies
echo "1. Installing documentation dependencies..."
pip install -r docs/requirements.txt

# Install the package in development mode (needed for mkdocstrings to find modules)
echo ""
echo "2. Installing package in development mode..."
pip install -e .

# Validate mkdocs.yml
echo ""
echo "3. Validating mkdocs.yml configuration..."
mkdocs --version

# Build documentation (this will catch any errors)
echo ""
echo "4. Building documentation..."
mkdocs build --strict

echo ""
echo "✅ Documentation build successful!"
echo ""
echo "To preview the documentation, run:"
echo "  mkdocs serve"
echo ""
echo "Then open http://127.0.0.1:8000 in your browser"

