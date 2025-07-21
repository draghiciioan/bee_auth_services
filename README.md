# BeeConect - Serviciu de Autentificare

[![CI](https://github.com/draghiciioan/bee_auth_services/actions/workflows/ci.yml/badge.svg)](https://github.com/draghiciioan/bee_auth_services/actions/workflows/ci.yml)

## Descriere Generală
BeeConect este o platformă scalabilă bazată pe microservicii, destinată conectării afacerilor cu clienții. Acest repository conține microserviciul de autentificare (`bee_auth_service`), responsabil pentru gestionarea identității utilizatorilor, autentificare și autorizare în ecosistemul BeeConect.

## Arhitectură
Platforma BeeConect folosește o arhitectură modernă bazată pe microservicii:

- **Entry Point**: Interfață globală a platformei prin aplicații web/mobile
- **API Gateway**: Distribuie cererile către microservicii (ex: Traefik)
- **RabbitMQ**: Router de evenimente pentru comunicare asincronă între servicii
- **Microservicii**: Servicii independente cu responsabilități specifice

### Microservicii Principale
- **auth_service** (acest repo): Autentificare, JWT, OAuth, 2FA
- **business_service**: Afaceri, puncte de lucru, abonamente
- **orders_service**: Comenzi, rezervări, statusuri
- **notifications_service**: Email/SMS, push-uri
- **payments_service**: Plăți Netopia, reconciliere

Fiecare microserviciu are propria bază de date PostgreSQL și poate fi dezvoltat, testat și deploiat independent.

## Tehnologii Utilizate
- **Backend**: FastAPI
- **ORM**: SQLAlchemy + Alembic
- **Autentificare**: JWT, OAuth2 (Google, Facebook)
- **Containerizare**: Docker/Docker Compose
- **Bază de date**: PostgreSQL
- **Mesagerie**: RabbitMQ

## Configurare și Rulare

### Cerințe
- Docker și Docker Compose
- Python 3.12+
- Poetry (pentru dezvoltare locală)

### Instalare și Rulare cu Docker
```bash
# Clonează repository-ul
git clone <repository-url>
cd bee_auth_services

# Construiește și rulează containerul
docker build -t bee-auth-service .
docker run -p 8000:8000 bee-auth-service
```

### Dezvoltare Locală
```bash
# Instalează dependențele
poetry install

# Notă: în `pyproject.toml` secțiunea `[tool.poetry]` setează `package-mode = false`,
# ceea ce permite instalarea doar a dependențelor fără împachetarea proiectului.

# Rulează serverul de dezvoltare
poetry run uvicorn main:app --reload
```

### Setarea variabilelor de mediu
Pentru funcționarea corectă sunt necesare următoarele variabile:
- `DATABASE_URL` – conexiunea la PostgreSQL
- `SECRET_KEY` – cheia de semnare a token-urilor
- `RABBITMQ_URL` – adresa RabbitMQ (opțional în dezvoltare)
- `CORS_ORIGINS` – lista de origini permise pentru CORS (separate prin virgule)

Exemplu:
```bash
export DATABASE_URL=postgresql://user:password@localhost/auth
export SECRET_KEY=supersecret
export RABBITMQ_URL=amqp://guest:guest@localhost/
export CORS_ORIGINS=https://app.example.com,https://admin.example.com
```

## Endpoints API
### Principale
- `GET /`: Verifică dacă serviciul rulează
- `GET /health`: Verifică starea serviciului
- `POST /register`
- `POST /login`
- `GET /verify-email`
- `POST /verify-2fa`
- `GET /auth/social/login`
- `POST /auth/social/callback`

### Exemple de solicitări
Înregistrare utilizator:
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com","password":"Secret123!","full_name":"New User"}'
```

Autentificare clasică:
```bash
curl -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"email":"new@example.com","password":"Secret123!"}'
```

Verificare email:
```bash
curl "http://localhost:8000/verify-email?token=<token>"
```

Verificare 2FA:
```bash
curl -X POST http://localhost:8000/verify-2fa \
  -H "Content-Type: application/json" \
  -d '{"twofa_token":"<token>"}'
```

Flux login social:
```bash
curl "http://localhost:8000/auth/social/login?provider=google"
curl -X POST http://localhost:8000/auth/social/callback \
  -H "Content-Type: application/json" \
  -d '{"provider":"google","token":"<oauth-token>"}'
```

### Migrare Bază de Date
Schema este gestionată cu **Alembic**. După setarea variabilei `DATABASE_URL`, rulează următoarele comenzi pentru a pregăti schema:

```bash
# Crează un nou script de migrare
alembic revision --autogenerate -m "descriere"

# Aplică toate migrațiile
alembic upgrade head
```

După aplicarea migrațiilor poți porni serviciul astfel:
```bash
poetry run uvicorn main:app --reload
```

### Testare
Pentru a rula testele unitare, folosește:
```bash
poetry run pytest
```

## Logging și Observabilitate
Jurnalizarea aplicației este configurată să emită mesaje în format JSON.
În mediul de producție, aceste loguri sunt colectate de un agent și trimise
către stack-ul ELK sau Loki pentru analiză și monitorizare.
Fiecare linie de log include informații precum `timestamp`, `user_id`,
`ip` și `endpoint` pentru a facilita depanarea și auditul.

## Integrare cu alte Microservicii
Acest serviciu de autentificare emite și validează token-uri JWT care sunt utilizate de celelalte microservicii pentru autorizare. Comunicarea asincronă se realizează prin RabbitMQ pentru evenimente precum înregistrarea utilizatorilor sau autentificarea.

### `bee.auth.events`
Pentru publicarea notificărilor se folosește exchange-ul `bee.auth.events` din RabbitMQ. Evenimentele sunt trimise cu biblioteca `aio-pika` prin helperul `emit_event`.

- **`user.registered`** – emis după crearea contului
  ```json
  {
    "event_id": "<uuid>",
    "timestamp": "2025-01-01T00:00:00Z",
    "user_id": "<uuid>",
    "email": "user@example.com"
  }
  ```
- **`user.logged_in`** – autentificare reușită
- **`user.2fa_requested`** – generare token 2FA
- **`user.email_verification_sent`** – trimiterea emailului de verificare

## Detalii JWT și validare

Tokenurile generate conțin informații de bază despre utilizator și expiră implicit după 2 ore. Payload-ul minimal este:

```json
{
  "sub": "<id_utilizator>",
  "email": "user@example.com",
  "role": "client",
  "provider": "local",
  "iat": 1710000000,
  "exp": 1710007200
}
```

### Trecerea la RS256

Implicit se folosește algoritmul **HS256** cu cheia definită în `SECRET_KEY`. Pentru semnarea asimetrică prin **RS256** setează variabila `JWT_ALGORITHM` la `RS256` și indică locația fișierelor cheie:

```bash
export JWT_ALGORITHM=RS256
export RSA_PRIVATE_KEY_PATH=/path/priv.pem
export RSA_PUBLIC_KEY_PATH=/path/pub.pem
```

Cheile pot fi generate rapid cu `openssl`:

```bash
openssl genrsa -out priv.pem 2048
openssl rsa -in priv.pem -pubout -out pub.pem
```

### Endpoint `/validate`

Exemplu de solicitare:

```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/validate
```

Răspuns pentru un token valid:

```json
{
  "valid": true,
  "user_id": "<id_utilizator>",
  "email": "user@example.com",
  "role": "client",
  "provider": "local"
}
```

Dacă un server Redis este configurat prin variabilele `REDIS_HOST` și `REDIS_PORT`, rezultatul decodificării tokenului este stocat temporar pentru a accelera validările ulterioare.

## Contribuție
Pentru a contribui la acest proiect, vă rugăm să urmați ghidul de contribuție și să respectați standardele de cod.

## Licență
Acest proiect este proprietar și confidențial. Toate drepturile rezervate.
