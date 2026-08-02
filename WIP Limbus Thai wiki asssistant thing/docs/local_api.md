# Local API

Run:

```powershell
python -m backend.api --host 127.0.0.1 --port 8765
```

Endpoints:

```text
GET /health
GET /identities/search?q=regret%20faust
GET /identities/{identity_id}?lang=th&uptie=4
GET /statuses?lang=th
GET /status/search?q=poise&lang=th
GET /bosses/search?q=status%20dummy
GET /bosses/{boss_id}
GET /assets/status/{status_key}
POST /simulate/clash  (raw/prototype; not real clash sequence yet)
```

Examples:

```text
http://127.0.0.1:8765/identities/search?q=regret%20faust
http://127.0.0.1:8765/identities/10207?lang=th&uptie=4
http://127.0.0.1:8765/statuses?lang=th
http://127.0.0.1:8765/status/search?q=poise&lang=th
http://127.0.0.1:8765/bosses/search?q=status%20dummy
http://127.0.0.1:8765/bosses/manual_status_dummy
http://127.0.0.1:8765/assets/status/Breath
```


Raw clash simulation example:

```powershell
$body = @{
  attacker = @{
    identity_id = "10215"
    skill = "skill_1"
    sp = 45
    uptie = 4
  }
  defender = @{
    identity_id = "10508"
    skill = "skill_1"
    sp = 0
    uptie = 4
  }
} | ConvertTo-Json -Depth 5

Invoke-WebRequest -UseBasicParsing `
  -Uri http://127.0.0.1:8765/simulate/clash `
  -Method POST `
  -ContentType "application/json" `
  -Body $body
```
This is intentionally small and standard-library-only for now. Discord and the future web app should use these endpoints or the same `backend.services` functions behind them.



Notes:

- /statuses returns every imported status row with a combat_rule annotation: partial, planned, alias, or display_only.
- /bosses/search and /bosses/{boss_id} currently read small manual boss fixtures from data/bosses/manual_bosses.json, not a full enemy import.
- /panic/search returns paired EN/TH PanicInfo rows when available.
- Identity profiles include raw wiki sanity data plus localized_sanity when PanicInfo can be matched from EN text.
