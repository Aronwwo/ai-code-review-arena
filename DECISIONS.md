# Architecture Decision Records (ADR)

This document captures key architectural and design decisions made during the development of AI Code Review Arena.

## Table of Contents

1. [Database Choice: SQLite vs PostgreSQL](#1-database-choice-sqlite-vs-postgresql)
2. [LLM Provider Architecture](#2-llm-provider-architecture)
3. [Conversation Orchestration Strategy](#3-conversation-orchestration-strategy)
4. [Frontend State Management](#4-frontend-state-management)
5. [Authentication Strategy](#5-authentication-strategy)
6. [Caching Strategy](#6-caching-strategy)
7. [File Storage Approach](#7-file-storage-approach)
8. [Agent Role Definitions](#8-agent-role-definitions)
9. [Review Parsing and Validation](#9-review-parsing-and-validation)
10. [Rate Limiting Implementation](#10-rate-limiting-implementation)

---

## 1. Database Choice: SQLite vs PostgreSQL

### Decision

Use **SQLite as the default** with PostgreSQL as an optional production alternative.

### Rationale

**Why SQLite default:**
- Zero configuration required - works out of the box
- Perfect for local development and small deployments
- No separate database server to manage
- Meets the "run in 10 minutes" requirement
- Sufficient for most use cases (single-user or small team)

**Why PostgreSQL support:**
- Better concurrent write performance for multi-user production
- Advanced features (full-text search, JSON operations, etc.)
- Industry standard for production web applications
- Easy migration path when scaling is needed

### Implementation

- SQLModel works seamlessly with both
- Connection string in `.env` determines which is used
- Docker Compose includes commented-out PostgreSQL service
- Same migrations work for both (SQLite and PostgreSQL compatible)

### Trade-offs

- SQLite limitations: weaker concurrency, no network access, 140TB size limit (non-issue here)
- Accepted because: vast majority of users will run locally or small-scale

---

## 2. LLM Provider Architecture

### Decision

Implement a **pluggable provider system** with a unified interface and graceful fallback chain.

### Rationale

**Multiple providers needed because:**
- Different users have different API access/preferences
- Free tiers have limits - users may want to switch
- Local-only option (Ollama) for privacy-conscious users
- Mock provider for testing and demos without API keys

**Fallback chain:**
1. User-specified provider + model
2. Default provider from config
3. Ollama (if running)
4. Mock provider (always works)

### Implementation

```
LLMProvider (ABC)
├── GroqProvider
├── GeminiProvider
├── CloudflareWorkersAIProvider
├── OllamaProvider
└── MockProvider

ProviderRouter
└── Selects provider based on config/availability
```

### Provider Selection Criteria

| Provider | Best For | Free Tier | Latency |
|----------|----------|-----------|---------|
| Groq | Fast responses | Yes, generous | Very low |
| Gemini | Advanced reasoning | Yes, 1500 RPD | Medium |
| Cloudflare | Edge deployment | Yes, limited | Low |
| Ollama | Privacy, offline | Unlimited | Medium-high |
| Mock | Testing, demos | Unlimited | Instant |

### Trade-offs

- More code complexity to support multiple providers
- Need to handle different error formats and rate limits
- Accepted because: flexibility is core requirement

---

## 3. Conversation Orchestration Strategy

### Decision

Implement **two distinct conversation modes** with different orchestration logic:

**Council Mode (Cooperative):**
- Round-robin agent turns (max 5 rounds)
- Each agent builds on previous comments
- Moderator synthesizes to structured JSON
- Focus: consensus and comprehensive coverage

**Arena Mode (Adversarial):**
- Fixed roles: Prosecutor → Defender → Moderator
- Single round debate on one specific issue
- Moderator renders binary verdict
- Focus: validation and severity calibration

### Rationale

**Why two modes:**
- Different cognitive benefits from cooperation vs. debate
- Cooperative mode explores the solution space
- Adversarial mode validates specific findings
- Mirrors real code review discussions (brainstorming vs. critique)

**Why structured turns:**
- Predictable cost (token usage)
- Clear narrative flow for users
- Easier to debug and test
- Avoids infinite loops

### Message Flow

**Council Mode:**
```
Turn 1: Agent A → Agent B → Agent C
Turn 2: Agent A (responds) → Agent B (responds) → Agent C (responds)
...
Turn N: Moderator synthesis
```

**Arena Mode:**
```
Prosecutor: "Issue X is critical because..."
Defender: "However, in this context..."
Moderator: { confirmed: true/false, final_severity: "...", ... }
```

### Trade-offs

- Limited turns may miss nuances
- Accepted because: cost control and UX clarity matter more
- Users can run multiple conversations if needed

---

## 4. Frontend State Management

### Decision

Use **TanStack Query (React Query)** for server state, React Context for auth, and local component state for UI.

### Rationale

**Why TanStack Query:**
- Purpose-built for server state synchronization
- Automatic caching, refetching, and background updates
- Excellent DevTools
- Reduces boilerplate compared to Redux
- Perfect for CRUD operations

**Why NOT Redux/Zustand:**
- Overkill for this app's complexity
- Most state is server-derived
- TanStack Query handles 90% of state needs

**Auth state:**
- React Context sufficient (small, infrequent changes)
- Token in localStorage, user object in context

**UI state:**
- Local useState/useReducer for forms, modals, filters
- No need for global store

### Implementation

```
TanStack Query:
- Projects, files, reviews, issues, conversations
- Mutations with optimistic updates
- Automatic cache invalidation

React Context:
- AuthContext (user, login, logout)

Component State:
- Form inputs, modal visibility, filter selections
```

### Trade-offs

- Learning curve for TanStack Query
- Accepted because: excellent documentation and huge productivity gains

---

## 5. Authentication Strategy

### Decision

Use **JWT (JSON Web Tokens)** with HTTP-only cookies (or Authorization header).

### Rationale

**Why JWT:**
- Stateless - no server-side session storage needed
- Works seamlessly with microservices/scaling
- Contains user ID and claims
- Standard, well-supported

**Why NOT session cookies:**
- Requires server-side session store (Redis/DB)
- Complicates horizontal scaling
- Less flexible for API clients

**Security measures:**
- Short expiration (1 hour default, configurable)
- bcrypt password hashing (cost factor 12)
- CORS properly configured
- Optional: refresh token rotation (future enhancement)

### Implementation

```python
# Login endpoint returns JWT
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}

# Frontend includes in requests:
Authorization: Bearer eyJ...
```

### Trade-offs

- JWT can't be invalidated before expiry (logout is client-side)
- Mitigation: short expiration + future blacklist for compromised tokens
- Accepted because: simplicity and statelessness outweigh edge cases

---

## 6. Caching Strategy

### Decision

**Two-level caching:**

1. **LLM Response Cache**: Cache by prompt hash (Redis or SQLite)
2. **HTTP Cache**: TanStack Query handles on frontend

### Rationale

**Why cache LLM responses:**
- Same code review should return same results (deterministic)
- Massive cost savings (API calls are expensive/rate-limited)
- Faster response times
- Hash includes: prompt + model + temperature + provider

**Why Redis for cache:**
- Fast (in-memory)
- Built-in TTL (automatic expiration)
- Widely used, well-tested
- Optional: fallback to SQLite table if Redis unavailable

**Cache invalidation:**
- TTL-based (24 hours default)
- Manual invalidation endpoint (admin only)
- Project/file changes don't auto-invalidate (user can re-run review)

### Implementation

```python
cache_key = hashlib.sha256(
    f"{provider}:{model}:{temperature}:{prompt}".encode()
).hexdigest()

# Try cache first
if cached := cache.get(cache_key):
    return cached

# Call LLM, then cache
response = provider.generate(...)
cache.set(cache_key, response, ttl=86400)
```

### Trade-offs

- Stale results if LLM model improves
- Mitigation: TTL + manual cache clear
- Accepted because: cost/speed benefits enormous

---

## 7. File Storage Approach

### Decision

Store **file content directly in database** (TEXT column).

### Rationale

**Why in-database:**
- Simple: no separate file storage service needed
- Atomic: files and metadata in same transaction
- Sufficient: most code files are small (<100KB)
- Portable: database backup includes all content
- Searchable: can query file content directly

**Why NOT object storage (S3, etc.):**
- Overkill for code files
- Extra dependency and configuration
- Cost (even if minimal)
- More failure modes

**Limits:**
- Max file size: 10MB (configurable)
- Max files per project: 100 (configurable)
- Sufficient for typical use case

### Implementation

```python
class File(SQLModel, table=True):
    content: str  # Full file content
    content_hash: str  # SHA256 for deduplication
    size_bytes: int
    language: str | None
```

### Trade-offs

- Database size grows with file count
- Accepted because: typical deployment has small DB (<1GB)
- Future: move to object storage if needed (easy migration)

---

## 8. Agent Role Definitions

### Decision

Implement **four specialized agent roles** with distinct system prompts:

1. **General Agent**: Overall code quality, best practices, maintainability
2. **Security Agent**: Vulnerabilities, security risks, input validation
3. **Performance Agent**: Algorithmic complexity, memory usage, bottlenecks
4. **Style Agent**: Code formatting, naming conventions, documentation

### Rationale

**Why four agents:**
- Covers primary code review concerns
- Each agent can have deep, focused system prompt
- Users can select subset (e.g., security-only review)
- Parallelizable (future optimization)

**Why NOT more agents:**
- Cost (each agent = API call)
- Cognitive load (too many perspectives)
- Diminishing returns

**Agent personas:**
- Each agent has a distinct "personality" in prompts
- Security agent is paranoid, catches edge cases
- Performance agent thinks about scale
- Style agent is pedantic about consistency

### Implementation

Each agent gets a structured prompt:
```
System: You are a {role} code reviewer. Focus on {focus_areas}...

User: Review this project:
- Language: {language}
- Files: {file_summaries}
- Full context: {selected_files}

Return JSON: { "issues": [...], "suggestions": [...] }
```

### Trade-offs

- Fixed set of agents (not user-customizable)
- Accepted because: covers 90% of needs, simpler UX

---

## 9. Review Parsing and Validation

### Decision

Use **JSON Schema with strict validation** and **fallback to best-effort parsing**.

### Rationale

**LLMs are unreliable:**
- Sometimes return invalid JSON
- Hallucinate extra fields
- Inconsistent formatting

**Strategy:**
1. Request strict JSON schema in prompt
2. Validate with Pydantic models
3. If validation fails, attempt regex extraction
4. Log parse failures for debugging
5. Return partial results rather than failing completely

### Implementation

```python
# Expected schema
class IssueSchema(BaseModel):
    severity: Literal["info", "warning", "error"]
    category: str
    title: str
    description: str
    file_name: str | None
    line_start: int | None
    line_end: int | None
    suggested_fix: str | None

# Validation
try:
    parsed = IssueSchema.model_validate_json(response)
except ValidationError:
    # Fallback: regex extraction
    parsed = extract_issues_fuzzy(response)
```

### Trade-offs

- Extra complexity in parsing logic
- Accepted because: robustness is critical for good UX

---

## 10. Rate Limiting Implementation

### Decision

Implement **per-user rate limiting** with Redis (or in-memory fallback).

### Rationale

**Why rate limit:**
- Prevent abuse (spam reviews)
- Protect LLM API quotas
- Ensure fair usage in multi-user scenarios
- DoS protection

**Granularity:**
- Per user (identified by JWT user_id)
- Per endpoint category (auth, reviews, conversations)
- Window: 1 minute (configurable)

**Limits:**
```
- Auth endpoints: 10/min
- Review creation: 5/min
- Conversation creation: 10/min
- File uploads: 20/min
- Read endpoints: 100/min
```

### Implementation

```python
# Redis-based with sliding window
key = f"ratelimit:{user_id}:{endpoint}"
current = redis.incr(key)
if current == 1:
    redis.expire(key, 60)  # 1 minute

if current > limit:
    raise HTTPException(429, "Rate limit exceeded")
```

**Fallback without Redis:**
- In-memory dict with timestamp pruning
- Lost on server restart (acceptable)

### Trade-offs

- Can be bypassed by creating multiple accounts
- Mitigation: email verification (future), IP-based limits (future)
- Accepted because: sufficient for honest users, deters casual abuse

---

## Summary of Key Principles

1. **Simplicity First**: Choose simple, proven solutions over cutting-edge
2. **Graceful Degradation**: App works even without API keys, Redis, etc.
3. **Developer Experience**: Fast setup, clear errors, good docs
4. **Cost Efficiency**: Cache aggressively, limit token usage, free tier friendly
5. **Security Conscious**: Rate limits, input validation, secure defaults
6. **Extensibility**: Pluggable providers, clear abstractions for future features

---

*This document is updated as new decisions are made. Last updated: 2025-11-28*
