# BeeConnect Auth Service

> **Versiune**: 1.0.0
> **Ultima actualizare**: 26 iulie 2025

## Cuprins

1. [Introducere](#introducere)
2. [Tehnologii cheie](#tehnologii-cheie)
3. [Structura proiectului](#structura-proiectului)
4. [Instalare și rulare rapidă](#instalare-și-rulare-rapidă)
5. [Variabile de mediu](#variabile-de-mediu)
6. [Fluxuri de autentificare](#fluxuri-de-autentificare)
7. [Baza de date](#baza-de-date)
8. [API Reference](#api-reference)
9. [Evenimente RabbitMQ](#evenimente-rabbitmq)
10. [Rate‑limiting & Securitate](#rate‑limiting--securitate)
11. [Ghid Dev & Testare](#ghid-dev--testare)
12. [Ghid Deploy (Docker & Kubernetes)](#ghid-deploy-docker--kubernetes)
13. [CI/CD](#cicd)
14. [Integrare React + Vite](#integrare-react--vite)
15. [FAQ](#faq)

---

## Introducere

`bee_auth_services` este microserviciul de autentificare și autorizare pentru platforma **BeeConnect**. Oferă:

* gestionarea conturilor, înregistrare și login clasic sau social (Google & Facebook);
* 2‑factor authentication (TOTP);
* resetare parolă prin e‑mail;
* emitere/refresh JWT (access & refresh);
* rate‑limit adaptiv și blocare cont;
* webhook‑uri/mesaje pe RabbitMQ pentru evenimente critice (ex. *UserRegistered*).

---

## Tehnologii cheie

| Tehnologie                 | Rol                             |
| -------------------------- | ------------------------------- |
| **FastAPI 1.1**            | Framework API REST              |
| **SQLAlchemy 2 + Alembic** | ORM & migrații DB               |
| **PostgreSQL**             | Baza de date principală         |
| **Redis**                  | Rate‑limiting & blacklist token |
| **PyJWT**                  | Generare/validare JWT           |
| **RabbitMQ (pika)**        | Event bus                       |
| **Prometheus + Grafana**   | Observabilitate (/metrics)      |
| **Sentry**                 | APM & alerting erori            |
| **pytest**                 | Testare unit & integrare        |
| **Docker & K8s**           | Deploy                          |

---

## Structura proiectului

```text
.
├── alembic/              # Migrații DB
├── events/               # Publicatori & clienți RabbitMQ
├── models/               # SQLAlchemy models
├── routers/              # End‑point‑uri FastAPI (v1/auth)
├── schemas/              # Pydantic request/response & event payloads
├── services/             # Logica de business (jwt, social, auth)
├── utils/                # Helper‑e: settings, security, rate_limit
├── tests/                # ~200+ teste → 96 % coverage
└── main.py               # Bootstrap aplicație FastAPI
```

---

## Instalare și rulare rapidă

```bash
# 1. Clonare & build imagine Docker
git clone https://github.com/beeconnect/bee_auth_services.git
cd bee_auth_services
docker build -t bee-auth-service .

# 2. Pornește servicii dependente
docker compose up -d postgres redis rabbitmq

# 3. Rulează microserviciul
docker run -p 8000:8000 --env-file .env.local bee-auth-service
```

Aplicația va fi disponibilă la `http://localhost:8000` iar documentația Swagger la `/docs`.

---

## Variabile de mediu

| Nume                 | Implicit                                        | Descriere                                            |
| -------------------- | ----------------------------------------------- | ---------------------------------------------------- |
| `ENVIRONMENT`        | `development`                                   | `production` activează Sentry & dezactivează reload  |
| `DATABASE_URL`       | `postgresql://user:password@postgres-auth/auth` | Conexiune PostgreSQL                                 |
| `SECRET_KEY`         | `secret`                                        | Cheia de semnare pentru JWT & TOTP                   |
| `JWT_ALGORITHM`      | `HS256`                                         | Algoritm criptografic                                |
| `ACCESS_TOKEN_EXP`   | `15`                                            | Minute, exp. token acces                             |
| `REFRESH_TOKEN_EXP`  | `1440`                                          | Minute, exp. token refresh                           |
| `REDIS_HOST/PORT/DB` | `redis/6379/0`                                  | Config Redis                                         |
| `RABBITMQ_URL`       | `amqp://guest:guest@rabbitmq/`                  | Brocker mesaje                                       |
| `EMAIL_SENDER`       |  -                                              | SMTP sending service                                 |
| `GOOGLE_*`           |  -                                              | Social login                                         |
| `FACEBOOK_*`         |  -                                              | Social login                                         |
| `ENABLE_METRICS`     | `false`                                         | Activează `/metrics`                                 |
| ...                  |                                                 | Consultați `utils/settings.py` pentru lista completă |

---

## Fluxuri de autentificare

### Login standard

```mermaid
sequenceDiagram
    participant C as Client
    participant API as Auth Service
    participant DB as PostgreSQL
    participant R as Redis
    C->>API: POST /v1/auth/login (email, parola)
    API->>DB: verif. user + hash parola
    alt cont blocat/too many attempts
        API-->>C: 429/403
    else success
        API->>R: store login attempt ok
        API->>API: generate JWT access+refresh
        API-->>C: 200 {access, refresh}
        API--)Rabbit: UserLoggedInEvent
    end
```

### Refresh token

```mermaid
sequenceDiagram
    C->>API: POST /v1/auth/refresh (refreshToken)
    API->>R: token în blacklist?
    alt invalid
        API-->>C: 401
    else
        API->>API: new JWT
        API-->>C: 200 {access, refresh}
    end
```

### 2FA TOTP

Fluxul complet (setup, verify, fallback e‑mail) este descris în `docs/flow_2fa.mmd`.

---

## Baza de date

```mermaid
erDiagram
    user ||..o{ email_verification : has
    user ||--o{ login_attempts : has
    user ||--o{ twofa_tokens : has
    user ||--o{ password_reset_token : has

    user {
        UUID id PK
        VARCHAR email
        VARCHAR password_hash
        VARCHAR role
        BOOLEAN is_active
        BOOLEAN is_email_verified
        BOOLEAN is_social
        VARCHAR provider
        TIMESTAMP created_at
    }
    email_verification {
        UUID id PK
        UUID user_id FK
        VARCHAR token
        TIMESTAMP expires_at
    }
    ...
```

---

## API Reference

> URL‑urile sunt prefixate cu **/v1/auth**.

| Metodă | Path               | Descriere                                | Auth necesar         |
| ------ | ------------------ | ---------------------------------------- | -------------------- |
| POST   | `/register`        | Creează cont & trimite e‑mail verificare | Nu                   |
| POST   | `/login`           | Autentificare clasică                    | Nu                   |
| GET    | `/social/login`    | Redirect OIDC (Google/Facebook)          | Nu                   |
| POST   | `/social/callback` | Finalizează login social                 | Nu                   |
| GET    | `/verify-email`    | Confirmă e‑mail                          | link token           |
| POST   | `/verify-2fa`      | Validează TOTP                           | Necesită `tmp_token` |
| POST   | `/request-reset`   | Inițiază resetare parolă                 | Nu                   |
| POST   | `/reset-password`  | Confirmă reset                           | token                |
| GET    | `/validate`        | Verifică access token                    | Bearer               |
| GET    | `/me`              | Date profil curent                       | Bearer               |
| POST   | `/setup-2fa`       | Activează 2FA                            | Bearer               |
| POST   | `/refresh`         | Obține token nou                         | Refresh              |
| POST   | `/logout`          | Invalidare refresh curent                | Refresh              |

### Exemple: `/login`

```http
POST /v1/auth/login
Content-Type: application/json

{
  "email": "dev@example.com",
  "password": "S3cr3t!23"
}
```

**Răspuns 200**

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_in": 900
}
```

*Consultați `/schemas/user.py` pentru toate structurile.*

---

## Evenimente RabbitMQ

| Event                        | Routing key               | Descriere           |
| ---------------------------- | ------------------------- | ------------------- |
| `UserRegisteredEvent`        | `auth.user.registered`    | Emit la creare cont |
| `EmailVerificationSentEvent` | `auth.user.email_sent`    | Mail verify trimis  |
| `UserLoggedInEvent`          | `auth.user.logged_in`     | Login success       |
| `TwoFARequestedEvent`        | `auth.user.2fa_requested` | Solicitare cod 2FA  |

Exemplu publicare *(simplificat)*:

```python
from events.rabbitmq import publish_event
publish_event("auth.user.logged_in", UserLoggedInEvent(user_id=id, email=email))
```

---

## Rate‑limiting & Securitate

* **FastAPILimiter + Redis**: `5` login încercări/minut → 429.
* **SecurityHeadersMiddleware** adaugă `X-Content-Type-Options`, `Referrer-Policy`, `Strict-Transport-Security`.
* **Password policy**: regex configurabil (default ≥8 caractere, 1 majusculă, 1 cifră, 1 simbol).

---

## Ghid Dev & Testare

```bash
# Lint + teste
poetry install --with dev
pre-commit run --all-files
pytest -q
```

> **Coverage**: `pytest --cov` ≈ 96 %.

---

## Ghid Deploy (Docker & Kubernetes)

### Docker Compose minimal

```yaml
version: "3"
services:
  auth:
    build: .
    env_file: .env.prod
    depends_on: [postgres, redis, rabbitmq]
    ports: ["8000:8000"]
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: auth
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
  redis:
    image: redis:7-alpine
  rabbitmq:
    image: rabbitmq:3-management
```

### Kubernetes (excerpt Helm values)

```yaml
authService:
  image:
    repository: ghcr.io/beeconnect/auth
    tag: 1.0.0
  env:
    DATABASE_URL: "postgresql://..."
    REDIS_URL: "redis://..."
  probes:
    readiness: "/health"
    liveness: "/health"
  resources:
    limits:
      cpu: "250m"
      memory: "256Mi"
```

---

## CI/CD

* `.github/workflows/ci.yml` rulează: lint → tests → docker build → push → helm chart update.
* Pentru rollback folosiți `helm rollback auth 3`.

---

## Integrare React + Vite

### 1. Instalare dependințe

```bash
npm i axios jwt-decode
```

### 2. `AuthContext.tsx`

```tsx
import { createContext, useContext, useState } from "react";
import axios from "axios";
import jwtDecode from "jwt-decode";

export const AuthCtx = createContext(null);
export const useAuth = () => useContext(AuthCtx);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(localStorage.getItem("access") ?? null);

  async function login(email, password) {
    const { data } = await axios.post("/v1/auth/login", { email, password });
    localStorage.setItem("access", data.access_token);
    localStorage.setItem("refresh", data.refresh_token);
    setToken(data.access_token);
  }

  async function refresh() {
    const { data } = await axios.post("/v1/auth/refresh", {
      refresh_token: localStorage.getItem("refresh"),
    });
    localStorage.setItem("access", data.access_token);
    setToken(data.access_token);
  }

  async function logout() {
    await axios.post("/v1/auth/logout", {
      refresh_token: localStorage.getItem("refresh"),
    });
    localStorage.clear();
    setToken(null);
  }

  const value = { token, login, refresh, logout };
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}
```

### 3. Protejarea rutelor

```tsx
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";

export function PrivateRoute({ children }) {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" />;
}
```

### 4. Exemplu login page

```tsx
function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        login(email, password);
      }}
      className="space-y-4"
    >
      <input
        className="border p-2 w-full"
        placeholder="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <input
        type="password"
        className="border p-2 w-full"
        placeholder="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button className="bg-amber-500 text-white w-full py-2 rounded">
        Login
      </button>
    </form>
  );
}
```

---

## FAQ

| Întrebare                             | Răspuns                                                         |
| ------------------------------------- | --------------------------------------------------------------- |
| **Cum schimb regex parolă?**          | Suprascrie `PASSWORD_REGEX` în `.env`.                          |
| **Cum adaug un nou provider social?** | Adaugă funcție în `services/social.py` și rute corespunzătoare. |
| **JWT expiră prea repede**            | Mărește `ACCESS_TOKEN_EXP` și `REFRESH_TOKEN_EXP`.              |

---

> Pentru orice feedback sau erori, deschide un issue pe GitHub ✨
