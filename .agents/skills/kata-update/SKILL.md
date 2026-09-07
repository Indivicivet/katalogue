---
name: kata-update
description: Help the user update or draft a karate kata entry in YAML format.
---

# Kata Update Skill

Use this skill when drafting, updating, or reviewing kata definitions in this repository.

## Repository Data Architecture

The catalog separates terminology dictionaries from kata definitions to guarantee referential integrity and consistency across styles:

- `techniques/stances.yaml`: Master dictionary of stances.
- `techniques/techniques.yaml`: Master dictionary of techniques (categorized into `block`, `punch`, `strike`, `kick`, and `other`).
- `equivalents.yaml`: Cross-discipline equivalence map (e.g. mapping Shotokan Heian to Shito-ryu Pinan).
- `kata/<style>/<number>_<name>.yaml`: Individual kata definitions (e.g. `kata/jka/01_heian_shodan.yaml`).

---

## Kata YAML Schema

Every kata file must adhere to the following schema:

```yaml
id: "01_heian_shodan"
name: "Heian Shodan"
kanji: "平安初段"
furigana: "へいあんしょだん"
style: "jka"
order: 1
status: "full_draft"      # early_draft | full_draft | student_reviewed | black_belt_reviewed | kata_book_reviewed | instructor_reviewed
last_updated: "2026-09-07"
reviewer: null            # MUST remain null until explicitly verified by a human reviewer
sources:                  # List of source references (books, video links, sensei manuals)
  - "Masatoshi Nakayama, Best Karate Vol. 5: Heian, Tekki"
tags:
  - "kyu_grade"
  - "9th_kyu"
  - "8th_kyu"
  - "shitei"
steps:
  - id: "1"
    count: 1
    subcount: null
    stance: "zenkutsu_dachi"
    lead: "left"          # left | right | both | none
    technique: "gedan_barai"
    secondary_technique: null
    target: "gedan"       # jodan | chudan | gedan | null
    turn: "left_90"       # 0 | left_90 | right_90 | left_180 | right_180 | left_45 | etc.
    facing: "W"           # N | S | E | W | NE | NW | SE | SW (relative to initial start facing North)
    kiai: false
    notes: "Turn left 90 deg into left front stance with downward block."
```

---

## Core Drafting Rules

### 1. Step Numbering and Splitting
- The base `count` integer must match the official canonical dojo count (e.g. 21 counts for Heian Shodan, 42 counts for Bassai Dai).
- **Sub-counts (`25a`, `25b`)**: Split a count into sub-moves only when multiple distinct tactical actions occur within that single count (for example, stomp `25a` followed by side elbow strike `25b` in Bassai Dai).
- **Never split preparation or chambering**: Ordinary chambering (such as pulling hand to hip `hiki-te` or loading a block) is part of the execution and must not be split into separate steps unless standard canonical literature explicitly numbers it.

### 2. Referential Integrity
- Every `stance` must exist in `techniques/stances.yaml`.
- Every `technique` and `secondary_technique` must exist in `techniques/techniques.yaml`.
- If a kata introduces a genuinely new stance or technique, add it to the corresponding master dictionary first, specifying its `kanji`, `furigana`, `romaji`, `en`, and `category`.

### 3. Direction and Rotation Consistency
- `facing` is the absolute compass direction relative to initial start facing North (`N`).
- `turn` describes the rotation from the previous step:
  - `0` or `advance`: No turn (straight ahead).
  - `left_90` / `right_90`: 90-degree turn.
  - `left_180` / `right_180`: 180-degree turn (disambiguates turning over left vs right shoulder).
  - `left_45`, `right_45`, `left_135`, `right_135`, `left_225`, `right_225`.
- Ensure the rotation from the previous facing equals the declared facing.

### 4. Human Review & Source Attribution
- **`reviewer`**: Must be `null` unless an actual human (student, black belt, instructor) has personally reviewed and confirmed the entry. AI assistants must never populate `reviewer` with their own name or references.
- **`sources`**: Use this field to document references, books (e.g. Nakayama's *Best Karate* series), and video links.
- **`status`**: New files start as `early_draft`. Once full sequences and counts are verified against canonical literature, they may be set to `full_draft`.

### 5. Notes Quality (Zero Slop)
- Avoid redundant filler notes. Do not write "Step 5 of Kanku Dai" or "Move 1 of Chinte"—the step ID already conveys this.
- If a step does not need additional clarifying tactical or footwork commentary, leave `notes: null`.

### 6. Cross-Discipline Equivalents
- When adding or modifying kata that have counterparts in other styles (e.g. Shotokan Heian and Shito-ryu Pinan), maintain `equivalents.yaml`.
- Remember historical swaps: Shotokan Heian Shodan corresponds to Shito-ryu Pinan Nidan; Heian Nidan corresponds to Shito-ryu Pinan Shodan.

### 7. Source Contradictions & Ambiguities (Flag to Human Reviewer Only)
- **Never guess or resolve conflicting sources silently.** If different authoritative sources disagree (for example, Nakayama specifies `kokutsu_dachi` while an official JKA tournament manual specifies `fudo_dachi` or `kiba_dachi`, or if sources differ on target height or lead hand), you MUST flag the contradiction directly to the user.
- **Internal Kata Inconsistencies**: If a movement transition, turn calculation, or limb positioning appears physically inconsistent or anomalous within the kata, explicitly highlight it for human review.
- **Do NOT pollute the YAML files**:
  - Keep the kata YAML files clean, minimal, and trustworthy.
  - Never write dispute logs, editorial debates, or discrepancy paragraphs into the step's `notes` field. If a note contains AI slop, clear it to `null`.
  - Keep the kata status as `early_draft`.
  - Present the conflicting evidence and specific open questions directly to the human reviewer in your chat response so they can make the authoritative decision or consult their sensei.
