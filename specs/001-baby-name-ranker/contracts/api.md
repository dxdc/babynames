# API Contract: Baby Name Discovery & Ranking App

## Authentication

All endpoints except `GET /api/names` and `GET /api/names/:id` require a valid JWT from Authentik in the `Authorization: Bearer <token>` header. The backend validates tokens against Authentik's JWKS endpoint.

Public endpoints (name browsing/detail) work without auth to support sharing and SEO.

## Endpoints

### Names (Public)

#### `GET /api/names`

Filter and paginate names.

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| q | string | | Free-text search on name |
| gender | M/F/U | | Filter by gender |
| origins | string[] | | Filter by origin slugs (comma-separated) |
| min_rank | int | | Minimum popularity rank (for "uncommon" names) |
| max_rank | int | | Maximum popularity rank |
| region | string | US | Region for popularity ranking |
| era_start | int | | Names peaking after this year |
| era_end | int | | Names peaking before this year |
| min_syllables | int | | |
| max_syllables | int | | |
| sort | string | rank | One of: rank, name, year_peak, random |
| page | int | 1 | |
| per_page | int | 50 | Max 200 |

**Response** (200):
```json
{
  "names": [
    {
      "id": "uuid",
      "display_name": "Catherine",
      "gender": "F",
      "origins": ["english", "french"],
      "meaning_short": "Pure",
      "rank": 42,
      "year_peak": 1956,
      "syllables": 3,
      "is_favourite": false
    }
  ],
  "total": 1234,
  "page": 1,
  "per_page": 50
}
```

Note: `is_favourite` is populated when user is authenticated, null otherwise.

#### `GET /api/names/:id`

Full name detail.

**Response** (200):
```json
{
  "id": "uuid",
  "display_name": "Catherine",
  "romanised_name": null,
  "gender": "F",
  "syllables": 3,
  "pronunciations": "K AE1 TH ER0 AH0 N",
  "total_count": 1825746,
  "year_min": 1880,
  "year_max": 2024,
  "year_peak": 1956,
  "is_biblical": null,
  "origins": [
    { "name": "English", "language_family": "Germanic", "region": "British Isles" },
    { "name": "French", "language_family": "Romance", "region": "Western Europe" }
  ],
  "meanings": [
    { "meaning": "Pure", "etymology": "From Greek katharos meaning 'pure'", "source": "Behind the Name" }
  ],
  "variants": [
    { "spelling": "Katherine", "popularity_rank": 1 },
    { "spelling": "Kathryn", "popularity_rank": 2 }
  ],
  "nicknames": ["Kate", "Katie", "Kathy", "Kitty", "Kay"],
  "popularity": [
    { "region": "US", "year": 2024, "rank": 302, "count": 1041 },
    { "region": "US", "year": 2023, "rank": 289, "count": 1098 }
  ],
  "is_favourite": false,
  "user_note": null,
  "user_rating": null
}
```

#### `GET /api/origins`

List all available origins for filter UI.

**Response** (200):
```json
{
  "origins": [
    { "slug": "celtic", "name": "Celtic", "name_count": 342 },
    { "slug": "hebrew", "name": "Hebrew", "name_count": 218 }
  ]
}
```

### Ranking (Authenticated)

#### `GET /api/ranking/leaderboard`

Current user's cumulative leaderboard.

**Query Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| limit | int | 20 | Top N names |
| settled_only | bool | false | Only names with low RD (high confidence) |

**Response** (200):
```json
{
  "leaderboard": [
    {
      "name_id": "uuid",
      "display_name": "Eleanor",
      "mu": 1823.4,
      "phi": 45.2,
      "comparisons": 18,
      "settled": true
    }
  ],
  "total_comparisons": 142
}
```

#### `GET /api/ranking/pair`

Get next pair for comparison. Algorithm prefers names with high uncertainty (phi).

**Query Parameters**: Same filter params as `GET /api/names` (to scope the round).

**Response** (200):
```json
{
  "name_a": { "id": "uuid", "display_name": "Eleanor", "origins": ["english"], "meaning_short": "Bright, shining one" },
  "name_b": { "id": "uuid", "display_name": "Genevieve", "origins": ["french", "celtic"], "meaning_short": "Woman of the people" }
}
```

#### `POST /api/ranking/compare`

Record a comparison result.

**Request**:
```json
{
  "winner_id": "uuid",
  "loser_id": "uuid",
  "round_label": "Celtic names, uncommon"
}
```

**Response** (200):
```json
{
  "winner": { "name_id": "uuid", "mu": 1612.3, "phi": 120.1 },
  "loser": { "name_id": "uuid", "mu": 1401.2, "phi": 115.8 },
  "total_comparisons": 143
}
```

### Favourites (Authenticated)

#### `GET /api/favourites`

**Response** (200):
```json
{
  "favourites": [
    { "name_id": "uuid", "display_name": "Eleanor", "note": "Grandma's name", "created_at": "2026-03-31T10:00:00Z" }
  ]
}
```

#### `POST /api/favourites`

```json
{ "name_id": "uuid", "note": "Optional note" }
```

#### `DELETE /api/favourites/:name_id`

#### `PATCH /api/favourites/:name_id`

```json
{ "note": "Updated note" }
```

### Collaboration (Authenticated)

#### `POST /api/sessions`

Create a collaborative session.

**Response** (201):
```json
{ "id": "uuid", "invite_code": "abc123", "invite_url": "https://app/join/abc123" }
```

#### `POST /api/sessions/join`

```json
{ "invite_code": "abc123" }
```

#### `GET /api/sessions/:id/compare`

Combined ranking view for all participants.

**Response** (200):
```json
{
  "participants": ["Alice", "Bob"],
  "strong_matches": [
    { "name_id": "uuid", "display_name": "Eleanor", "scores": [1823.4, 1756.2], "agreement": 0.92 }
  ],
  "discussion_points": [
    { "name_id": "uuid", "display_name": "Bartholomew", "scores": [1801.1, 1234.5], "agreement": 0.31 }
  ]
}
```

## Error Format

All errors follow:
```json
{
  "error": "short_code",
  "message": "Human-readable description",
  "detail": {}
}
```

HTTP status codes: 400 (bad request), 401 (not authenticated), 403 (not authorised), 404 (not found), 422 (validation error), 500 (server error).
