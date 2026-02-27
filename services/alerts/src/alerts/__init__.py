"""
VoxSentinel Alert Dispatch Service.

Routes keyword matches, sentiment escalations, compliance violations,
and intent detection events to configured alert channels (WebSocket,
webhooks, Slack, etc.) with throttling and deduplication.
"""
