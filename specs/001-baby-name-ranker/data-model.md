# Data Model: Baby Name Discovery & Ranking App

## Entity Relationship Overview

```
User (Authentik) ──┬── Favourite ──── Name
                   ├── RankingState ── Name
                   └── Participant ──── CollaborativeSession

Name ──┬── NameOrigin ──── Origin
       ├── NameMeaning
       ├── PopularityRecord
       └── Variant (self-referencing group)
```

## Entities

### Name

The core entity. One record per phonetically distinct name.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| display_name | text | Most common spelling (e.g. "Catherine") |
| romanised_name | text | Romanised form if non-Latin, null otherwise |
| gender | enum | M, F, or U (unisex) |
| syllables | int | Number of syllables |
| first_letter | char | First letter |
| total_count | int | Total births across all spellings (US SSA) |
| year_min | int | First year appearing in data |
| year_max | int | Last year appearing in data |
| year_peak | int | Year with highest count |
| pronunciations | text | ARPABET phonetic transcriptions |
| is_biblical | text | Biblical category (Person/Place/God/Other) or null |
| unisex_pct | float | Minority gender share (0–50) or null |

**Unique constraint**: (display_name, gender)

### Origin

Cultural/linguistic origin category.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| name | text | Origin name (e.g. "Celtic", "Hebrew", "Old English") |
| language_family | text | Broader grouping (e.g. "Indo-European", "Semitic") |
| region | text | Geographic region (e.g. "British Isles", "Middle East") |

### NameOrigin (join table)

Many-to-many: a name can have multiple origins.

| Field | Type | Description |
|-------|------|-------------|
| name_id | UUID | FK → Name |
| origin_id | UUID | FK → Origin |

### NameMeaning

One or more meanings per name.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| name_id | UUID | FK → Name |
| meaning | text | Description of the meaning |
| etymology | text | Linguistic history/derivation |
| source | text | Data source (e.g. "Behind the Name") |

### PopularityRecord

Name popularity in a specific region and year.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| name_id | UUID | FK → Name |
| region | text | Region code (e.g. "US", "UK", "AU-NSW") |
| year | int | Year |
| rank | int | Popularity rank that year in that region |
| count | int | Number of births (if available) |

**Index**: (name_id, region, year) — primary query path for trend charts

### Variant

Links alternative spellings/forms of the same name.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| name_id | UUID | FK → Name (the variant) |
| group_id | UUID | Shared group identifier for all variants of the same name |
| spelling | text | This variant's spelling |
| popularity_rank | int | Relative popularity of this spelling |

### User

Managed by Authentik. The app stores a local reference.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key (matches Authentik subject ID) |
| display_name | text | From Authentik profile |
| email | text | From Authentik profile |
| created_at | timestamp | First login |
| last_active | timestamp | Last API interaction |

### Favourite

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | FK → User |
| name_id | UUID | FK → Name |
| note | text | Optional personal note |
| created_at | timestamp | When favourited |

**Unique constraint**: (user_id, name_id)

### RankingState

Glicko-2 rating for a name from a specific user's perspective. Cumulative across all rounds.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | FK → User |
| name_id | UUID | FK → Name |
| mu | float | Glicko-2 rating (default 1500) |
| phi | float | Rating deviation — uncertainty (default 350) |
| sigma | float | Volatility (default 0.06) |
| wins | int | Total wins |
| losses | int | Total losses |
| comparisons | int | Total comparisons |
| updated_at | timestamp | Last comparison involving this name |

**Unique constraint**: (user_id, name_id)

### ComparisonHistory

Audit trail of individual pairwise comparisons.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | FK → User |
| winner_name_id | UUID | FK → Name |
| loser_name_id | UUID | FK → Name |
| round_label | text | Optional label for the round (e.g. filter description) |
| created_at | timestamp | When the comparison was made |

### CollaborativeSession

Links multiple users for combined ranking view.

| Field | Type | Description |
|-------|------|-------------|
| id | UUID | Primary key |
| created_by | UUID | FK → User |
| invite_code | text | Shareable code/link for joining |
| created_at | timestamp | |

### SessionParticipant

| Field | Type | Description |
|-------|------|-------------|
| session_id | UUID | FK → CollaborativeSession |
| user_id | UUID | FK → User |
| joined_at | timestamp | |

**Unique constraint**: (session_id, user_id)

## Key Query Patterns

1. **Filter names**: SELECT from Name JOIN NameOrigin/Origin with WHERE clauses on origin, popularity, era, gender, etc. Paginated.
2. **Name detail**: SELECT Name + JOIN NameMeaning + NameOrigin + PopularityRecord + Variant for a single name.
3. **Popularity chart**: SELECT PopularityRecord WHERE name_id = X AND region = Y ORDER BY year.
4. **Leaderboard**: SELECT RankingState WHERE user_id = X ORDER BY mu DESC. Filter by phi for "settled" names.
5. **Next pair**: SELECT from pool of names in current filter set, weighted by phi (prefer uncertain names) and avoiding recent comparisons.
6. **Collaborative overlap**: SELECT ranking states for two users, JOIN on name_id, calculate agreement score.
7. **Favourites**: SELECT Favourite JOIN Name WHERE user_id = X.
