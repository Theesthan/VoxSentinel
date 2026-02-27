"""
Sentiment gauge component for VoxSentinel dashboard.

Renders a real-time sentiment indicator showing rolling 30-second
average sentiment per stream or speaker.
"""

from __future__ import annotations

import streamlit as st
