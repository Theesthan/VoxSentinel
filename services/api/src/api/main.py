"""
FastAPI application entry point for VoxSentinel API gateway.

Creates and configures the FastAPI app, registers routers, middleware,
startup/shutdown event handlers, and exposes the ASGI application.
"""

from __future__ import annotations

from fastapi import FastAPI
