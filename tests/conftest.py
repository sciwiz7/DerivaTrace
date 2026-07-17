import os
import sys

# Make the tests/ directory importable so shared fixtures / the conformance
# registry can be imported by every test module regardless of import mode.
sys.path.insert(0, os.path.dirname(__file__))
