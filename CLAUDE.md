# Plex Music Enhancer – Claude Development Context

**Last Updated:** 2026-07-11  
**Project:** Plex Music Enhancer (v1.0.14 → v1.1.0)  
**Owner:** Timo Königin (Steinbecker Softwaredienste)  
**Repo:** https://github.com/amylasehai0z/plex-music-enhancer

---

## 🎵 Project Overview

**Plex Music Enhancer** ist ein produktionsreifes Python-Tool zur intelligenten Anreicherung von Plex-Musikmetadaten mit AI-gestützten deutschen Beschreibungen für Künstler und Alben.

### Current Architecture
- **Backend:** Python 3.12+ (FastAPI REST, CLI via Typer)
- **Frontend:** React 18 + TypeScript (Vite, Mantine UI)
- **Infrastructure:** Docker, Synology DS920+, GitHub Actions CI/CD
- **AI Provider:** OpenAI (GPT-5.5), DummyProvider für Tests
- **External Providers:** MusicBrainz, Wikipedia, Discogs, Last.fm

### Key Components
```
src/plex_music_enhancer/
├── ai/              # AI Provider abstraction (OpenAI, Dummy)
├── album_reviews/   # Album-specific review pipeline
├── apply/           # Safe write-back: Backup → Verify → Audit
├── batch/           # Batch processing with queue
├── editorial/       # Style Engine + Context Builders
├── enrichment/      # Metadata fetching & composition
├── planner/         # Action classification (CREATE/TRANSLATE/IMPROVE/REVIEW/SKIP)
├── providers/       # External metadata sources
├── quality/         # QA validation + scoring
├── review/          # Review document models
├── verification/    # Fact verification + confidence scoring
└── web/             # FastAPI + React frontend
```

---

## 🎯 Current Status (v1.0.14)

### ✅ Completed
- Plex Read/Write pipeline (safe, backed up, verified)
- Album Review full integration (Preview → Review → Apply)
- Artist Page with all actions (Preview, Apply, Open in Plex, Refresh)
- Docker/Synology setup (persistent /config/exports for backups)
- Multi-arch builds (linux/amd64 + linux/arm64)
- CI fully green (Python 3.12 + 3.13, Container tests)

### ⏳ Next Priority: Artist Planner (v1.1.0)

**Goal:** Intelligent action classification for Artist Biographies

**Pattern:** Reuse Album Planner design

Album Planner (existing, ref: `src/plex_music_enhancer/planner/album.py`):
- **CREATE** → No usable summary exists
- **TRANSLATE** → Existing summary is English
- **IMPROVE** → German but quality score < 60
- **REVIEW** → Ambiguous or score 60-80 (user decides)
- **SKIP** → German & score > 80

### Implementation Tasks

#### Phase 1: Artist Planner Backend
- [ ] `src/plex_music_enhancer/planner/artist.py` – Mirror AlbumPlanner logic
- [ ] Content Quality scoring for Artist bios (same rules as Album)
- [ ] API endpoints in `web/routers/` for Artist planning
- [ ] Unit tests in `tests/test_artist_planner.py`

#### Phase 2: Artist Page Smart Actions
- [ ] Replace simple "Generate" button with action-based buttons
- [ ] Show planner recommendation (CREATE/TRANSLATE/etc.)
- [ ] Integrate with existing Apply pipeline
- [ ] Live status updates during generation

#### Phase 3: Testing + CI
- [ ] All tests pass locally (`pytest`)
- [ ] GitHub Actions CI green
- [ ] Version bump: 1.0.14 → 1.1.0

---

## 🔧 Local Setup (Your Mac)

```bash
# Already done (venv activated)
cd ~/Developer/plex-music-enhancer/plex-music-enhancer
source .venv/bin/activate

# Key commands
python -m pytest                    # Run all tests
black . && ruff check .             # Linting
cd web && npm test && npm run build # Frontend
python -m build                     # Package
docker build -t plex-enhancer:local .  # Build image locally

# Run locally
plex-enhancer login                 # Configure Plex
plex-enhancer doctor                # Verify setup
python -m plex_music_enhancer.web   # Start REST API (http://127.0.0.1:8080)
```

### Environment Variables
```bash
PLEX_ENHANCER_PLEX_URL=http://localhost:32400
PLEX_ENHANCER_PLEX_TOKEN=<your-token>
PLEX_ENHANCER_AI__PROVIDER=dummy  # Use DummyProvider for dev/testing
OPENAI_API_KEY=<optional, only if testing real AI>
```

---

## 📁 Key Files to Know

### Backend
- `src/plex_music_enhancer/planner/album.py` – **Reference for Artist Planner**
- `src/plex_music_enhancer/editorial/artist.py` – Artist biography composition
- `src/plex_music_enhancer/quality/engine.py` – Quality scoring (reuse for both)
- `src/plex_music_enhancer/apply/service.py` – Safe write-back (handles both Album & Artist)
- `tests/test_artist_workflow.py` – Existing Artist tests (extend this)

### Frontend
- `web/src/pages/ArtistsPage.tsx` – Artist list page (update action buttons here)
- `web/src/pages/AlbumsPage.tsx` – **Reference for Artist UX**
- `web/src/hooks/useApi.ts` – API integration (add Artist Planner mutations)
- `web/src/components/StatusPill.tsx` – Action status indicator

### Configuration
- `prompts/artist_biography.md` – Prompt template (already optimized)
- `pyproject.toml` – Dependencies & build config
- `docker-compose.yml` – Local testing setup

---

## 🎨 Code Style & Conventions

### Python
- **Format:** Black (configured in `pyproject.toml`)
- **Lint:** Ruff
- **Type Hints:** Required for all public functions
- **Docstrings:** Google-style, focused on "why" not "what"
- **Tests:** Pytest, one test file per module

### TypeScript/React
- **Components:** Function components + hooks only
- **State Management:** React Query for server state
- **Styling:** Mantine UI components (no custom CSS unless necessary)
- **Naming:** camelCase for functions, PascalCase for components
- **Tests:** Vitest (see `web/vitest.setup.ts`)

### Git Commits
- **Format:** `type: short description` (e.g., `feat: add artist planner backend`)
- **Types:** feat, fix, refactor, test, docs, chore
- **Scope:** `(artist-planner)`, `(apply)`, etc. when specific

---

## 🔄 Workflow: From Repo to Production

1. **Local Development**
   ```bash
   git checkout -b feat/artist-planner
   # Make changes, test locally
   python -m pytest
   black . && ruff check .
   ```

2. **Push to GitHub**
   ```bash
   git add .
   git commit -m "feat(artist-planner): implement backend classification"
   git push origin feat/artist-planner
   ```

3. **GitHub Actions Runs Automatically**
   - Python 3.12 & 3.13 tests
   - Ruff + Black linting
   - Frontend tests (`npm test`)
   - Docker multi-arch build
   - GHCR push (if main branch)

4. **Create Pull Request** → Merge when CI green

5. **Release** → Tag `v1.1.0` → GitHub Actions auto-creates release

---

## 🚀 Quick Commands

```bash
# View current Artist implementation
grep -r "artist" src/plex_music_enhancer/apply/ | head -20

# Check existing Album Planner (your reference)
cat src/plex_music_enhancer/planner/album.py | head -100

# Run tests for Artist workflow
pytest tests/test_artist_workflow.py -v

# Quick API check
curl http://127.0.0.1:8080/api/v1/system/health

# View recent commits
git log --oneline -10
```

---

## 📚 References

### Documentation
- **User Manual:** `assets/pdf/Plex-Music-Enhancer-Handbuch.pdf` (Deutsch, v1.1)
- **Backend API:** `docs/backend-api.md`
- **Review System:** `docs/review-system.md`
- **Docker/Synology:** `docs/docker.md`

### Architecture Guides
- **Planner Design:** `docs/planner.md` (Apply this pattern to Artists)
- **Editorial Engine:** `docs/editorial.md`
- **Quality System:** `docs/quality.md`

### Test Patterns
- Album tests: `tests/test_album_reviews.py`
- Planner tests: `tests/test_planner.py`
- API tests: `tests/test_rest_api.py`

---

## 🎯 Success Criteria for v1.1.0

- [ ] Artist Planner backend complete & tested
- [ ] Smart action buttons on Artists page
- [ ] All tests pass (`pytest` + `npm test`)
- [ ] GitHub Actions CI fully green
- [ ] Version bumped to 1.1.0 in `pyproject.toml` + `package.json`
- [ ] CHANGELOG updated
- [ ] Release created on GitHub

---

## 💡 Common Gotchas

1. **Plex Connection:** Must be accessible from container (use `http://plex:32400` in Docker)
2. **Rate Limits:** OpenAI has per-minute limits; use `PLEX_ENHANCER_PERFORMANCE__MAX_WORKERS=2` in prod
3. **Tests:** DummyProvider generates deterministic text; real AI tests may timeout
4. **Frontend Hot Reload:** Use `npm run dev` in `web/` for development
5. **Docker Volumes:** `/config/exports` must be persistent for backups to survive container restarts

---

## 📞 Questions? Debug Tips?

1. **Check logs:** `~/.plex-enhancer/logs/` or Docker logs via Portainer
2. **Enable verbose:** `plex-enhancer --log-level DEBUG <command>`
3. **Inspect Plex:** `plex-enhancer inspect library --name "Music"`
4. **Check cache:** `plex-enhancer cache stats`
5. **Reset for clean test:** `plex-enhancer cache clear`

---

**Happy coding! 🚀**  
This context is maintained by Claude – update this file as you discover new patterns or gotchas.
