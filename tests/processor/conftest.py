import sys
import os

# Allow test files to import processor modules directly
# (e.g. `from consistent_hash import ConsistentHashRing`)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/processor"))
