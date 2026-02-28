"""
Prometheus metrics helpers for VoxSentinel.

Provides shared metric definitions and registration utilities
for exposing Prometheus-format metrics from all services, including
request counters, latency histograms, and service-specific gauges.
"""

from __future__ import annotations

