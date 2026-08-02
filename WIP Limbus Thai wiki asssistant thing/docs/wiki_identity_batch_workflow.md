# Wiki Identity Batch Workflow

Download wiki Identity pages with image folders:

```powershell
python work\download_wiki_identity_html.py --out inputs\wiki_identity_html --workers 5 --image-workers 4 --delay 0
```

Test with only a few pages:

```powershell
python work\download_wiki_identity_html.py --limit 5 --out inputs\wiki_identity_html_test_download --workers 5 --image-workers 4 --delay 0
```

Import downloaded HTML into wiki draft JSON:

```powershell
python work\import_wiki_html_identities.py inputs\wiki_identity_html --out outputs\wiki_identity_imports.json --summary outputs\wiki_identity_imports_summary.md
```

Link wiki drafts to localization data and rebuild the review/editor page:

```powershell
python work\link_wiki_import_to_localization.py
```

Open:

```text
outputs/wiki_identity_localized_review.html
```

Use `Download All JSON` in the review page to export one batch file for the bot/database seed.

