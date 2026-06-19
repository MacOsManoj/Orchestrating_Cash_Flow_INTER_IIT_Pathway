
import os
import sys
from app.forex.pipeline import PipelineConfig

# Mock config path
config_path = os.path.abspath("app/forex/config.yaml")

try:
    config = PipelineConfig.from_yaml(config_path)
    
    print(f"Config Path: {config_path}")
    print(f"Resolving base dir: {os.path.dirname(config_path)}")
    print(f"Resolved Data Dir: {config.data_dir}")
    
    expected_suffix = "app/forex/data/"
    if config.data_dir.endswith(expected_suffix):
        print("SUCCESS: Data dir points to correct location.")
    else:
        print(f"FAILURE: Data dir expected to end with '{expected_suffix}', but got '{config.data_dir}'")
        sys.exit(1)

except Exception as e:
    print(f"Error loading config: {e}")
    sys.exit(1)
