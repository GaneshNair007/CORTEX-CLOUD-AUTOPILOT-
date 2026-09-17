"""
CORTEX Cloud Autopilot — Control Plane Orchestration
"""

try:
    from backend.control_plane.pipeline import ControlPlanePipeline, control_plane
except ImportError:
    from control_plane.pipeline import ControlPlanePipeline, control_plane

__all__ = ["ControlPlanePipeline", "control_plane"]
