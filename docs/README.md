# Documentation

This directory contains the source files for the DaMiao motor driver documentation.

## Testing the Documentation

### Quick Test

Run the test script from the project root:

```bash
./test_docs.sh
```

This will:
1. Install all documentation dependencies
2. Install the package in development mode
3. Validate the configuration
4. Build the documentation

### Manual Testing

1. **Install dependencies:**
   ```bash
   pip install -r docs/requirements.txt
   pip install -e .
   ```

2. **Validate configuration:**
   ```bash
   mkdocs --version
   mkdocs build --strict
   ```

3. **Serve locally (with live reload):**
   ```bash
   mkdocs serve
   ```
   Then open http://127.0.0.1:8000 in your browser

4. **Build static site:**
   ```bash
   mkdocs build
   ```
   The built site will be in the `site/` directory.

### Testing Auto-Generated API Docs

The API reference pages use `mkdocstrings` to auto-generate documentation from docstrings. To verify this works:

1. Make sure the package is installed: `pip install -e .`
2. Build the docs: `mkdocs build`
3. Check the API pages in the `site/api/` directory
4. Verify that class methods, parameters, and docstrings are rendered correctly

## Documentation Structure

- `index.md` - Homepage
- `getting-started/` - Installation and quick start guides
- `api/` - API reference (auto-generated from docstrings)
- `configuration/` - Configuration guides

## Deployment

Documentation is automatically deployed to GitHub Pages via GitHub Actions when changes are pushed to the main branch.
