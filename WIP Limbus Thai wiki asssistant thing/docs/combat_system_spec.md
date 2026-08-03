# Limbus Assistant Combat System Spec

This document is the source of truth for the simulator. Do not add Discord or website combat commands until the relevant section here is understood and implemented.

## Current Truth

The current simulator is only a raw roll helper. It is not a real Limbus Company combat simulator yet.

It can calculate:

- heads chance from SP
- raw skill roll distribution
- simple final roll comparison

It does not correctly model:

- repeated clash rounds
- coin breaking
- unbreakable coins
- defense skill behavior
- speed and targeting
- offense level vs defense level
- status/passive/script effects
- damage after clash
- enemy/boss mechanics

## Real Clash Sequence

A clash is not one final roll comparison.

Each clash round:

1. Each side rolls using its current remaining clashable coins.
2. Compare the current clash power.
3. The losing side loses/breaks one clashable coin.
4. Repeat until the clash is resolved.
5. The winner attacks with remaining usable coins.

Example:

```text
Attacker:
Base 3, coins +4 +4 +4, all heads
Current power = 15

Defender:
Base 5, coins +2 +2 +2, all tails
Current power = 5

Round 1: 15 vs 5 -> defender loses 1 coin
Round 2: 15 vs 5 -> defender loses 1 coin
Round 3: 15 vs 5 -> defender loses final coin

Attacker wins clash and attacks with 3 remaining coins.
```

The old raw distribution calculator incorrectly treats this as a single `15 vs 5` comparison.

## First Correct Simulator Target

Implement `simulate_clash_sequence` before Discord `/clash`.

Inputs:

- attacker base power
- attacker coin powers
- attacker SP
- defender base power
- defender coin powers
- defender SP
- optional fixed coin results for deterministic testing
- optional unbreakable coin flags later

Outputs:

- clash winner
- round-by-round log
- coins remaining on each side
- final attack coins
- warnings for ignored mechanics

## Deterministic Test Cases

### All Attacker Heads, All Defender Tails

```text
attacker: base 3, +4 +4 +4
defender: base 5, +2 +2 +2
```

Expected:

- attacker wins every clash round
- defender loses 3 coins
- attacker keeps 3 coins
- attacker wins the clash

### Attacker Loses One Round

Create a case where attacker loses the first round and verify attacker loses one coin before the next roll.

### Tie Rule

Confirm exact tie behavior from source before implementing. Do not guess.

## Rules Still Need Confirmation

- Exact tie behavior in clash rounds.
- Which coin breaks when a side loses.
- Whether broken coin selection differs for plus, minus, reused, or special coins.
- Exact unbreakable coin behavior.
- How evade/guard/counter resolve during clash.
- How offense/defense level affects clash power.
- When SP changes apply during clash/combat.

## Data Sources We Already Have

Identity wiki HTML has useful combat-state metadata:

- stagger thresholds
- panic type
- low morale / panic text
- sanity increase factors
- sanity decrease factors

The importer now parses this, but old exported JSON/SQLite must be rebuilt before all fields appear in the API.

## Data Needed Later

- Enemy and boss skills.
- Enemy and boss body part resistances.
- Stagger thresholds.
- Skill script effects.
- Status effect executable rules.
- Passive executable rules.

## Implementation Order

1. Keep raw roll helper, but label it as raw.
2. Add deterministic clash-sequence function.
3. Add probability calculation over clash sequences.
4. Add manual enemy skill input.
5. Add enemy/boss data import.
6. Add Discord `/clash` only after the sequence result is credible.

