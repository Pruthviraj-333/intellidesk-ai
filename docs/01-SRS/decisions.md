# SRS Decision Log

| # | Question | Decision | Date |
|---|----------|----------|------|
| 1 | Email Provider | **Gmail SMTP** (free, widely supported) | 2026-07-06 |
| 2 | Real-time Updates | **WebSockets** (Socket.IO) with polling fallback | 2026-07-06 |
| 3 | Ticket ID Format | **TKT-YYYYMMDD-XXXX** confirmed | 2026-07-06 |
| 4 | SLA Defaults | Keep proposed defaults (Critical: 15min/4hr, High: 1hr/8hr, Medium: 4hr/24hr, Low: 8hr/72hr) | 2026-07-06 |
| 5 | ML Training Data | **LLM-based prediction only** for v1.0. ML models will be added later when real data accumulates. | 2026-07-06 |
