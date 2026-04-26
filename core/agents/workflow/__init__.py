"""Workflow orchestration submodule.

This module provides:
- build_workflow: Construct the workflow graph
- create_initial_state: Create the initial workflow state
- run_workflow: Execute the end-to-end workflow
"""

from core.agents.workflow.builder import build_workflow, create_initial_state
from core.agents.workflow.routing import should_regenerate

# Import run_workflow from parent module for backward compatibility
import sys
import importlib.util
from pathlib import Path

# Load the workflow.py entry point
_entry_path = Path(__file__).parent.parent / "workflow.py"
if _entry_path.exists():
    _spec = importlib.util.spec_from_file_location("_workflow_entry", _entry_path)
    _module = importlib.util.module_from_spec(_spec)
    sys.modules["_workflow_entry"] = _module
    _spec.loader.exec_module(_module)
    run_workflow = _module.run_workflow
else:
    def run_workflow(*args, **kwargs):
        raise ImportError("workflow.py entry point not found")

__all__ = [
    "build_workflow",
    "create_initial_state",
    "should_regenerate",
    "run_workflow",
]