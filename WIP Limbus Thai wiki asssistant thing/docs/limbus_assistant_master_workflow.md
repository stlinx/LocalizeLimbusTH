# Limbus Assistant Master Workflow

Project name: **Limbus Assistant**

Purpose: build a Discord-first AI assistant for Limbus Company that can answer gameplay/localization questions, show identity data, calculate combat outcomes, recommend teams, read screenshots, and later power a website/web app from the same backend.

This document is the calm master plan. When the project feels confusing, come back here and continue from the current milestone.

## Core Rule

Discord bot, website, admin tools, AI assistant, simulator, and OCR must all use the same backend services and database.

Do not duplicate game logic in the Discord bot or website.

```text
Discord / Website / Admin Panel
  -> API Backend
  -> SQLite now, PostgreSQL later
  -> Simulator / OCR / Recommendation / Localization tools
```

The LLM should not guess exact game data. It should search the database, call simulator tools, and explain the result.

## Current Status

Already working:

- Identity database imported from wiki/html/localization data.
- SQLite database exists.
- Local API exists.
- Website preview exists at `http://127.0.0.1:8765/`.
- Identity search works.
- Thai/English identity profile data works.
- Status lookup works.
- Skill/status/coin images mostly work.
- Discord-style identity card renderer works.
- Thai shaping in rendered PNG cards is fixed.
- Special skill variants can use separate skill ids instead of one shared `skill_3` image.
- Basic raw roll helper exists.
- `POST /simulate/clash` exists, but it is raw/prototype only and should not be treated as real clash yet.

Still early / not complete:

- Real clash sequence engine is not built yet.
- Damage formula is not implemented yet.
- E.G.O data is not imported into the real database yet.
- Enemy/boss data is not imported yet.
- AI assistant `/ask` is not built yet.
- Admin panel is not built yet.
- OCR is not built yet.
- Team recommendation is not built yet.

## Build Order

### Milestone 1: Stabilize Current Identity Data

Goal: make the current identity lookup/card system reliable enough that future work can trust it.

Tasks:

1. Add validation for all identity records.
2. Check every identity has:
   - id
   - English name
   - Thai/localized name when available
   - sinner
   - rarity
   - HP
   - defense level
   - slash/pierce/blunt resistances
   - skills
   - passives
3. Detect missing skill icons, status icons, and identity images.
4. Create a validation report for bad/missing records.
5. Keep website preview as review/debug UI.

Done when:

- Validation report shows no critical errors.
- Missing assets are listed clearly.
- Discord card rendering does not crash for all identities.

### Milestone 2: Basic Combat Simulator

Goal: make the project more than a database viewer.

Tasks:

1. Create `simulator/` module.
2. Implement:
   - `heads_chance(sp)`
   - plus coin final power
   - minus coin final power
   - skill roll distribution
   - clash win/lose/tie probability
3. Use existing identity skill data from SQLite.
4. Add tests for simple plus-coin and minus-coin cases.

Important:

- Start with raw skill power only.
- Do not try to support every special passive/status script yet.
- Return warnings when special mechanics are ignored.

Done when:

- We can calculate clash odds between two normal skills.
- Result includes assumptions and warnings.
Current status:

- Basic raw roll distribution is implemented.
- Plus coins and minus coins are handled from SQLite/raw mechanics.
- Status effects, passives, offense/defense level, resonance, and special scripts are warning-only for now.

### Milestone 3: Real Clash Sequence

Goal: replace the raw roll comparison with real clash rounds and coin breaking.

Tasks:

1. Write and maintain `docs/combat_system_spec.md`.
2. Implement deterministic clash rounds:
   - both sides roll current remaining coins
   - compare current power
   - loser breaks/loses one coin
   - repeat until resolved
3. Add tests using fixed heads/tails results.
4. Confirm tie behavior before implementing tie cases.
5. Keep status/passive/special scripts as warnings until implemented.
6. Update `POST /simulate/clash` to use the real sequence engine.

Done when:

- Deterministic clash examples match expected in-game behavior.
- API returns a round-by-round clash log.
- The result clearly lists remaining coins and final attack coins.

### Milestone 4: Clash API + Discord Command

Goal: expose credible clash calculation through Discord after the engine is corrected.

Tasks:

1. Keep `POST /simulate/clash` as the shared backend tool.
2. Add manual enemy skill input.
3. Add Discord `/clash` command that calls the API.
4. Show assumptions/warnings in the Discord response.

Done when:

- Discord users can run a clash calculation that uses clash rounds, not single final-roll comparison.
- The website/API can call the same calculation.

### Milestone 5: Basic Damage Calculator

Goal: calculate simple expected damage after skill rolls.

Tasks:

1. Implement basic damage formula.
2. Include:
   - final power
   - offense vs defense level
   - slash/pierce/blunt resistance
   - coin count
3. Add `POST /simulate/damage`.
4. Add Discord `/damage`.

Important:

- Start simple.
- Mark status/passive/special scripts as ignored until implemented.

Done when:

- Basic damage range/expected damage works for normal attacks.

### Milestone 6: AI Assistant Query Layer

Goal: let users ask natural questions without making the LLM guess.

Tasks:

1. Add `POST /assistant/query`.
2. Start with a simple router:
   - identity lookup
   - status lookup
   - localization lookup
   - clash request
   - damage request
3. Add tool-call style internal functions:
   - `search_identity`
   - `get_identity_profile`
   - `search_status`
   - `calculate_clash`
   - `calculate_damage`
4. Log:
   - user question
   - detected intent
   - tools used
   - answer
   - warnings/missing data
5. Add Discord `/ask`.

Done when:

- User can ask "How do I play Regret Faust?" and the assistant searches data before answering.
- User can ask "What does Poise do?" and it uses status data.
- User can ask for clash/damage and it calls simulator tools.

### Milestone 7: E.G.O Import

Goal: add E.G.O as first-class game data.

Tasks:

1. Import E.G.O names, skills, passives, resources, risk levels, and localization.
2. Link E.G.O to sinners.
3. Add E.G.O search/profile API.
4. Add E.G.O card/render preview if useful.
5. Add Discord `/ego`.

Done when:

- Users can search E.G.O and see awakening/corrosion/passive text.
- Identity recommendation can mention compatible E.G.O later.

### Milestone 7.5: Status Rule Registry and Manual Boss Fixtures

Goal: make status effects visible to the simulator without pretending every effect is fully implemented.

Current status:

- All imported status rows can be listed from SQLite.
- `simulator/statuses.py` maps common statuses to combat rule buckets.
- Most statuses are marked `display_only` until reviewed.
- `data/bosses/manual_bosses.json` holds 1-2 small manual boss fixtures for simulator testing.
- Status source rule: EN/TH localization remains the primary bot text source; saved wiki Status Effects HTML is backup/mechanics reference.

Tasks:

1. Expand common status rules in small reviewed batches.
2. Keep each rule marked as `partial`, `planned`, `alias`, or `display_only`.
3. Use manual boss fixtures for early combat tests.
4. Import full enemy/boss data only after the simulator model is stable.

Done when:

- The simulator can explain which statuses it applies and which it ignores.
- A small curated boss can be used for clash/damage/team tests.

### Milestone 8: Enemy and Boss Data

Goal: prepare for useful matchup and recommendation features.

Tasks:

1. Start with 1-2 manual boss fixtures for testing.
2. Import enemies and bosses only after the data model is proven.
3. Store:
   - HP
   - speed
   - stagger thresholds
   - body parts
   - resistances
   - skills
   - special mechanics notes
4. Add boss search/profile API.
5. Add Discord `/boss`.

Done when:

- Users can search boss data.
- Clash/damage can use enemy/boss defense and resistance data.

### Milestone 9: Admin / Expert Knowledge

Goal: let trusted people improve data without editing raw JSON manually.

Tasks:

1. Create admin tables:
   - strategy notes
   - team recommendations
   - data corrections
   - audit log
   - review status
2. Add basic admin edit UI.
3. Add reviewed/published states.
4. Make bot prefer reviewed data.

Done when:

- Experts can add strategy notes.
- Bot answers can cite admin notes.
- Changes are auditable.

### Milestone 10: Team Recommendation

Goal: recommend teams based on roster, boss, archetype, and notes.

Tasks:

1. Add user roster storage.
2. Add simple archetype tags:
   - Burn
   - Bleed
   - Sinking
   - Poise
   - Tremor
   - Rupture
   - Charge
3. Add rule-based scoring.
4. Use boss weaknesses and admin notes.
5. Add Discord `/recommend`.

Done when:

- User can ask for a team against a boss.
- Bot explains why each unit is recommended.

### Milestone 11: OCR / Screenshot Reading

Goal: let users send screenshots instead of typing everything.

Tasks:

1. Start with roster screenshot OCR.
2. Use text OCR for names.
3. Use template/icon matching for portraits/status icons.
4. Return confidence scores.
5. Ask user to confirm/correct uncertain results.
6. Save corrected roster data.

Done when:

- User uploads roster screenshot.
- Bot detects likely identities.
- User can confirm and save roster.

### Milestone 12: Website Becomes Real App

Goal: move beyond debug preview after backend/bot are stable.

Tasks:

1. Database browser pages.
2. Identity/E.G.O/status/boss pages.
3. User roster management.
4. Strategy note browsing.
5. Localization search.
6. Later interactive combat simulator.

Done when:

- Website uses the same API as Discord.
- Users can manage roster and browse game data comfortably.

## AI Assistant Design

The assistant should behave like this:

```text
User asks question
  -> classify intent
  -> call exact tool
  -> answer using tool result
  -> include warnings if data is incomplete
  -> log question and tool result for future improvement
```

Allowed early intents:

- `identity_lookup`
- `status_lookup`
- `localization_lookup`
- `clash_calc`
- `damage_calc`
- `team_recommendation_later`
- `ocr_later`

Examples:

```text
"How do I play Regret Faust?"
  -> search_identity
  -> get_identity_profile
  -> summarize skills/passives/status keywords

"What does Poise do?"
  -> search_status
  -> answer from status database

"Can Skill 2 clash this boss skill?"
  -> find skills
  -> calculate_clash
  -> explain odds
```

Never let the LLM invent exact numbers. Exact numbers must come from database or simulator.

## Data Rules

Keep these stable:

- Raw localization files are source text, not full battle data.
- Wiki/html import gives useful battle data, but still needs validation.
- SQLite is fine now.
- Later production can move to PostgreSQL.
- Store patch/source info when possible.
- Prefer structured data over plain text.
- Keep import/export scripts repeatable.

## Peaceful Work Rhythm

Use this order when working:

1. Pick one milestone.
2. Build the smallest useful version.
3. Validate with one known identity.
4. Validate with weird identities that have variants.
5. Add API endpoint.
6. Add Discord command only after API works.
7. Add website/debug preview only if it helps review.
8. Write down what is missing.
9. Move to next milestone.

Do not chase every visual bug forever unless it blocks bot/API reliability.

## Immediate Next Step

Build **Milestone 3: Real Clash Sequence**.

The raw API endpoint already exists:

```text
POST /simulate/clash
```

Recommended next task:

```text
Implement simulate_clash_sequence with round-by-round coin breaking.
```

Do this before Discord `/clash`.

Discord should not expose the raw single-roll comparison as if it were real.

## Reference Docs

- `outputs/limbus_ai_assistant_architecture.md`
- `docs/local_api.md`
- `docs/combat_system_spec.md`
- `docs/wiki_identity_batch_workflow.md`
- `outputs/identity_data_shape_from_wiki_sample.md`
- `outputs/localization_import_report.md`
- `outputs/wiki_identity_imports_summary.md`



