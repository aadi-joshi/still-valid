"""Offline validator for Boolean plans after a world-state change.

The replay rule is fixed: apply the stated change, then walk the ordered
plan. A step with an unmet precondition does not apply its effects.
"""

__version__ = "1.0.0"
