# Declare all targets as .PHONY
.PHONY: main clean test build

# Variable definitions
PYTHON := python3
CLEAN_DIRS := *.egg-info
CLEAN_FILES := *.json
UNFURL_DIR:= athena

# Main target
build: $(UNFURL_DIR)
	$(PYTHON) -m pip install .

# Clean target
clean:
	find -type d -name __pycache__ -exec rm -rfv {} +
	rm -f $(CLEAN_FILES)
	rm -rf $(CLEAN_DIRS) build/
