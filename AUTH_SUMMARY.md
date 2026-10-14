# MISTIQ 2.0 - Auth Implementation Summary

## Backend
- **Models**: User (id, username unique, password_hash, role, student_id FK unique, created_at), AuthSession (token_hash unique, user_id FK, expires_at)
- **Security**: PBKDF2-SHA256 with per-user salt, opaque tokens (SHA-256 hash stored), session expiry
- **Auth Service**: Registration creates Student record, admin seeding from MISTIQ_ADMIN_USERNAME/MISTIQ_ADMIN_PASSWORD (defaults admin/admin)
- **API**: /api/auth/register, /api/auth/login, /api/auth/me, /api/auth/logout (public). All other /api/* require auth except /health
- **Protection**: /research/* and /showcase/* require admin; student-scoped routes enforce ownership; students list/create admin-only
- **DB**: DATABASE_URL normalized (postgres→psycopg), SQLite fallback to backend/mistiq.db, pool_pre_ping enabled

## Frontend
- **AuthContext**: Manages user/token state, persists to localStorage (mistiq.token)
- **API Client**: Attaches Bearer token, handles 401 (clear+redirect) and 403
- **Login**: Sign in/Create account tabs with username/password; name required for registration
- **Routing**: Role-based nav, RequireAdmin guards for /research*
- **Types**: AuthUser, AuthResponse, UserRole

## Tests
- Backend: 69 tests pass (including test_auth.py)
- Frontend: builds successfully with tsc --noEmit clean

## Notes
- AMPA model unchanged; SQLite canonical; no retraining; production-ready auth