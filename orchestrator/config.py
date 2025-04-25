# orchestrator/config.py
import os
import yaml

def load_config(path: str) -> dict:
    """
    Load a YAML config file and substitute ${VAR} with environment variables.
    """
    with open(path, "r") as f:
        raw = f.read()
    # simple ${VAR} interpolation
    for key, val in os.environ.items():
        raw = raw.replace(f"${{{key}}}", val)
    return yaml.safe_load(raw)
