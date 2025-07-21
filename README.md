# BeeConect - Serviciu de Autentificare

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

# Rulează serverul de dezvoltare
poetry run uvicorn main:app --reload
```

### Setarea variabilelor de mediu
Pentru funcționarea corectă sunt necesare următoarele variabile:
- `DATABASE_URL` – conexiunea la PostgreSQL
- `SECRET_KEY` – cheia de semnare a token-urilor
- `RABBITMQ_URL` – adresa RabbitMQ (opțional în dezvoltare)

Exemplu:
```bash
export DATABASE_URL=postgresql://user:password@localhost/auth
export SECRET_KEY=supersecret
export RABBITMQ_URL=amqp://guest:guest@localhost/
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

## Integrare cu alte Microservicii
Acest serviciu de autentificare emite și validează token-uri JWT care sunt utilizate de celelalte microservicii pentru autorizare. Comunicarea asincronă se realizează prin RabbitMQ pentru evenimente precum înregistrarea utilizatorilor sau autentificarea.

## Contribuție
Pentru a contribui la acest proiect, vă rugăm să urmați ghidul de contribuție și să respectați standardele de cod.

## Licență
Acest proiect este proprietar și confidențial. Toate drepturile rezervate.