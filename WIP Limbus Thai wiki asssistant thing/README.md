# Limbus Assistant

Discord-first Limbus Company assistant prototype with shared backend API, curated game database, identity/boss data browser, and simulator experiments.

## Local run

```powershell
python -m pip install -r requirements.txt
python -m backend.api
```

Then open:

```txt
http://127.0.0.1:8765/
```

## Notes

- Copy `.env.example` to `.env` and fill private values locally.
- Do not commit `.env`.
- `inputs/` contains raw downloaded wiki/local files and is intentionally not included.
- `outputs/web_assets/` is included because the local web/API uses those small prepared image assets.
