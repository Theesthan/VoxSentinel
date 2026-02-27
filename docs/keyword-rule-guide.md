# Keyword Rule Configuration Guide

## VoxSentinel Keyword Rule System

### Overview

VoxSentinel's NLP service uses a multi-strategy keyword detection engine that supports:

- **Exact matching** via Aho-Corasick automaton (O(n) scan time)
- **Fuzzy matching** via RapidFuzz (configurable Levenshtein distance threshold)
- **Regex patterns** for complex pattern matching
- **Sliding window** context-aware matching across transcript segments

### Creating a Keyword Rule

#### Via API

```bash
curl -X POST http://localhost:8000/api/v1/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Threat Detection",
    "keywords": ["bomb", "threat", "weapon", "explosive"],
    "match_strategy": "aho_corasick",
    "severity": "critical",
    "fuzzy_threshold": 0.85,
    "enabled": true
  }'
```

#### Via Dashboard

Navigate to **Settings > Keyword Rules** in the Streamlit dashboard.

### Match Strategies

| Strategy | Use Case | Performance | Accuracy |
|----------|----------|-------------|----------|
| `aho_corasick` | Exact multi-keyword scanning | O(n) — fastest | Exact only |
| `fuzzy` | Misspellings, ASR errors | Slower | Configurable threshold |
| `regex` | Complex patterns, dates, codes | Moderate | Pattern-dependent |
| `sliding_window` | Context-aware multi-segment | Moderate | High |

### Severity Levels

| Level | Description | Default Channels |
|-------|-------------|-----------------|
| `low` | Informational | WebSocket only |
| `medium` | Notable | WebSocket, Dashboard |
| `high` | Urgent | WebSocket, Slack, Email |
| `critical` | Immediate action required | All channels |

### Fuzzy Matching Threshold

The `fuzzy_threshold` parameter (0.0–1.0) controls how similar a word must be to trigger a match:

- **0.90–1.0**: Very strict (near-exact matches only)
- **0.80–0.89**: Recommended for most use cases
- **0.70–0.79**: Catches more ASR transcription errors
- **< 0.70**: High false-positive rate, not recommended

### Best Practices

1. Start with exact matching (`aho_corasick`) for known keywords
2. Add fuzzy rules only for keywords commonly mistranscribed by ASR
3. Use regex for structured patterns (phone numbers, codes)
4. Set appropriate severity levels to avoid alert fatigue
5. Regularly review and tune rules based on false-positive rates
