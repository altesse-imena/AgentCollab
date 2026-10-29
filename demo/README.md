# Recorded demo runs

`runs.json` holds real runs exported with `agentcollab export`. The deployed demo imports it
at startup and replays them, so visitors can watch the agents without any model calls.

To record new ones (needs an API key and Docker):

```bash
cd backend
.venv/bin/agentcollab eval --label demo --tasks sql_injection,lru_cache,retry_decorator
.venv/bin/agentcollab runs                        # find the run ids
.venv/bin/agentcollab export <run ids> -o ../demo/runs.json
```
