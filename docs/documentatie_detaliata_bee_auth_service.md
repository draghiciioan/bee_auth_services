# Serviciul de Autentificare BeeConect - Documentație Detaliată

## Prezentare Generală

Serviciul de Autentificare BeeConect este un microserviciu responsabil pentru autentificarea și autorizarea utilizatorilor în cadrul platformei BeeConect. Acesta oferă funcționalități pentru înregistrarea utilizatorilor, autentificare, verificarea e-mailului, autentificarea în doi pași și validarea token-urilor. Serviciul este construit folosind FastAPI, SQLAlchemy și PostgreSQL, cu integrări suplimentare pentru mesageria RabbitMQ, cache-ul Redis și monitorizarea Prometheus.

## Structura Proiectului

Proiectul urmează o structură modulară cu o separare clară a responsabilităților:

```
bee_auth_services/
├── alembic/                  # Scripturi de migrare a bazei de date
├── docs/                     # Fișiere de documentație
├── events/                   # Gestionarea evenimentelor (RabbitMQ)
├── models/                   # Modele de bază de date
├── routers/                  # Definiții de rute API
├── schemas/                  # Scheme Pydantic pentru validare
├── services/                 # Servicii de logică de afaceri
├── tests/                    # Suite de teste
├── utils/                    # Funcții utilitare
├── main.py                   # Punctul de intrare al aplicației
├── database.py               # Configurarea conexiunii la baza de date
├── Dockerfile                # Definiția containerului
└── pyproject.toml            # Dependențele proiectului
```

## Explicarea Fișierelor Principale

### Fișiere Principale ale Aplicației

#### `main.py`

Punctul de intrare pentru aplicația FastAPI. Acest fișier:
- Inițializează aplicația FastAPI
- Configurează middleware-ul (CORS, headere de securitate)
- Configurează limitarea ratei cu Redis
- Configurează metricile Prometheus
- Integrează Sentry pentru urmărirea erorilor
- Definește endpoint-uri de bază pentru verificarea stării
- Include router-ul de autentificare

Componente cheie:
- Funcția `lifespan`: Gestionează pornirea/oprirea aplicației, inițializează conexiunea Redis
- Handler de excepții: Capturează și procesează excepțiile negestionate
- Endpoint de verificare a stării: Oferă informații despre starea serviciului

#### `database.py`

Gestionează conexiunea la baza de date și managementul sesiunilor folosind SQLAlchemy. Acest fișier:
- Definește URL-ul de conexiune la baza de date din variabilele de mediu
- Creează motorul SQLAlchemy și fabrica de sesiuni
- Oferă clasa Base pentru moștenirea modelelor

#### `pyproject.toml`

Definește metadatele proiectului și dependențele folosind Poetry. Dependențele cheie includ:
- FastAPI: Framework web
- SQLAlchemy: ORM pentru operațiuni de bază de date
- Alembic: Instrument de migrare a bazei de date
- Passlib: Hashing de parole
- Python-jose: Gestionarea token-urilor JWT
- Aio-pika: Client RabbitMQ
- Redis: Pentru limitarea ratei și cache
- Prometheus: Pentru colectarea metricilor

### Modele

#### `models/user.py`

Definește modelul User pentru stocarea informațiilor contului utilizatorului:
- Cheie primară UUID
- Email, parolă hash-uită, nume și informații de contact
- Control de acces bazat pe roluri (client, admin_business, curier, colaborator, superadmin)
- Flag-uri de stare a contului (activ, email verificat)
- Integrare cu autentificare socială (furnizor, ID social)
- Timestamp-uri pentru creare și actualizări

#### `models/email_verification.py`

Gestionează token-urile de verificare a e-mailului:
- Se leagă de un utilizator prin cheie străină
- Stochează un token unic de verificare
- Include timestamp de expirare
- Urmărește timpul de creare

#### `models/twofa_tokens.py`

Gestionează token-urile de autentificare în doi pași:
- Se leagă de un utilizator prin cheie străină
- Stochează token-uri de autentificare
- Urmărește starea de utilizare a token-ului
- Include timestamp de expirare
- Înregistrează timpul de creare

#### `models/login_attempts.py`

Urmărește încercările de autentificare pentru monitorizarea securității:
- Înregistrează atât încercările de autentificare reușite, cât și cele eșuate
- Stochează adresa IP și informațiile despre agentul utilizatorului
- Se leagă de contul utilizatorului când este posibil
- Include timestamp pentru momentul în care a avut loc încercarea

### Routere

#### `routers/auth.py`

Definește toate endpoint-urile API legate de autentificare:
- `/register`: Înregistrarea utilizatorului cu verificare prin e-mail
- `/login`: Autentificarea utilizatorului cu 2FA opțional
- `/social-login` și `/social-callback`: Autentificare prin social media
- `/verify-email`: Endpoint de verificare a e-mailului
- `/verify-twofa`: Verificarea autentificării în doi pași
- `/validate`: Endpoint de validare a token-ului
- `/me`: Recuperarea informațiilor utilizatorului curent

Fiecare endpoint se integrează cu serviciile și modelele corespunzătoare, implementează limitarea ratei și emite evenimente când este necesar.

### Servicii

#### `services/auth.py`

Implementează logica de afaceri de bază pentru autentificare:
- `create_email_verification`: Generează token-uri de verificare a e-mailului
- `record_login_attempt`: Înregistrează încercările de autentificare pentru securitate
- `create_twofa_token`: Creează token-uri de autentificare în doi pași

Constantele definesc timpii de expirare a token-urilor:
- Token-uri de verificare a e-mailului: 15 minute
- Token-uri 2FA: 5 minute

#### `services/jwt.py`

Gestionează generarea și validarea token-urilor JWT:
- Suportă atât algoritmii de semnare HMAC (HS256), cât și RSA (RS256)
- Implementează crearea token-urilor cu informații despre utilizator și expirare
- Oferă validarea și decodarea token-urilor
- Se integrează cu Redis pentru cache-ul token-urilor
- Suportă rotația cheilor secrete pentru securitate

### Scheme

#### `schemas/user.py`

Definește modele Pydantic pentru validarea cererii/răspunsului:
- `UserCreate`: Validarea cererii de înregistrare
- `UserLogin`: Validarea credențialelor de autentificare
- `UserRead`: Formatul răspunsului cu informații despre utilizator
- `SocialLogin`: Validarea datelor de autentificare socială
- `TwoFAVerify`: Validarea cererii de verificare în doi pași

#### `schemas/event.py`

Definește structurile de evenimente pentru mesageria RabbitMQ:
- `UserRegisteredEvent`: Emis când un utilizator se înregistrează
- `UserLoggedInEvent`: Emis la autentificarea cu succes
- `EmailVerificationSentEvent`: Urmărește verificarea e-mailului
- `TwoFARequestedEvent`: Semnalează inițierea 2FA

### Evenimente

#### `events/rabbitmq.py`

Gestionează mesageria asincronă cu RabbitMQ:
- Stabilește conexiunea la serverul RabbitMQ
- Definește configurația de exchange și coadă
- Implementează funcționalitatea de emitere a evenimentelor
- Oferă publicare structurată a evenimentelor

### Utilitare

#### `utils/security.py`

Implementează utilitare legate de securitate:
- Hashing și verificare a parolelor folosind bcrypt
- Configurarea headerelor de securitate
- Validarea și sanitizarea intrărilor

#### `utils/token_store.py`

Gestionează cache-ul token-urilor în Redis:
- Stochează token-uri cu expirare
- Recuperează token-uri din cache
- Gestionează invalidarea token-urilor

#### `utils/logging.py`

Configurează logarea structurată:
- Configurează formatarea log-urilor JSON
- Configurează nivelurile de log bazate pe mediu
- Implementează urmărirea ID-ului cererii

#### `utils/metrics.py`

Implementează colectarea metricilor Prometheus:
- Urmărește ratele de succes/eșec ale autentificării
- Monitorizează performanța endpoint-urilor API
- Înregistrează numărul de erori

#### `utils/alerts.py`

Gestionează alertele pentru probleme critice:
- Se integrează cu sistemele de monitorizare
- Declanșează alerte pentru evenimente de securitate
- Procesează notificări bazate pe praguri

## Migrări de Bază de Date

### `alembic/`

Conține scripturi de migrare a bazei de date:
- `env.py`: Configurează mediul de migrare
- `versions/`: Conține scripturi individuale de migrare
  - `1c572a13dc24_create_auth_tables.py`: Crearea inițială a schemei
  - `35b6c0f1d431_update_login_attempts.py`: Actualizări pentru urmărirea autentificărilor

## Testare

### `tests/`

Suite de teste cuprinzătoare care acoperă:
- Fluxuri de autentificare (înregistrare, autentificare)
- Procesul de verificare a e-mailului
- Autentificarea în doi pași
- Validarea token-urilor
- Caracteristici de securitate (CORS, headere)
- Emiterea evenimentelor
- Limitarea ratei
- Colectarea metricilor

## Configurare

Serviciul este configurat prin variabile de mediu:
- `DATABASE_URL`: String de conexiune PostgreSQL
- `SECRET_KEY`: Cheie de semnare JWT
- `REDIS_HOST`, `REDIS_PORT`: Conexiune Redis
- `RABBITMQ_URL`: Conexiune RabbitMQ
- `CORS_ORIGINS`: Origini permise pentru CORS
- `ENVIRONMENT`: Mediu de rulare (development/production)
- `SENTRY_DSN`: Urmărirea erorilor Sentry

## Deployment

### `Dockerfile`

Definește imaginea containerului pentru deployment:
- Folosește imaginea de bază Python 3.12
- Instalează Poetry și dependențele
- Configurează aplicația pentru producție
- Configurează verificări de sănătate
- Expune portul serviciului

## Caracteristici de Securitate

Serviciul implementează multiple măsuri de securitate:
- Hashing de parole cu bcrypt
- Autentificare bazată pe JWT
- Limitarea ratei pentru a preveni atacurile de forță brută
- Urmărirea încercărilor de autentificare
- Autentificare în doi pași
- Verificare e-mail
- Headere de securitate (HSTS, CSP, etc.)
- Suport pentru rotația cheilor secrete

## Puncte de Integrare

Serviciul se integrează cu mai multe sisteme externe:
- PostgreSQL: Stocare primară de date
- Redis: Limitarea ratei și cache-ul token-urilor
- RabbitMQ: Mesageria evenimentelor
- Prometheus: Colectarea metricilor
- Sentry: Urmărirea erorilor

## Concluzie

Serviciul de Autentificare BeeConect oferă o soluție de autentificare sigură și scalabilă pentru platforma BeeConect. Designul său modular permite întreținerea și extinderea ușoară, în timp ce caracteristicile sale cuprinzătoare de securitate asigură protecția datelor utilizatorilor.