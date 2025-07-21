# Ghid pentru Agenți BeeConect

## Introducere

Acest document este destinat agenților care lucrează cu platforma BeeConect, oferind o înțelegere detaliată a arhitecturii, fluxurilor de lucru și implementării tehnice. BeeConect este o platformă scalabilă bazată pe microservicii, proiectată pentru a conecta afacerile cu clienții într-un mod eficient și modern.

## Arhitectură Detaliată

### Viziune de Ansamblu

BeeConect folosește o arhitectură modernă de microservicii, care permite:
- Dezvoltare independentă a componentelor
- Scalabilitate pe componente individuale
- Reziliență sporită (un serviciu căzut nu afectează întregul sistem)
- Tehnologii specializate pentru fiecare componentă

### Componente Principale

#### 1. Entry Point
- **BeeConect** - interfața globală a platformei
- Utilizatorii interacționează prin aplicații web/mobile
- Oferă o experiență unitară, deși în spate sunt multiple microservicii

#### 2. API Gateway (Traefik)
- Funcționează ca reverse proxy care distribuie cererile către microservicii
- Implementează:
  - Rate limiting (limitarea numărului de cereri)
  - Routing inteligent
  - Header injection pentru JWT
  - Load balancing

#### 3. RabbitMQ - Router de Evenimente
- **Rol central**: Primește evenimente de la servicii și le transmite către consumatori
- **Exemple de evenimente**: user_created, order_placed
- **Consumatori tipici**: notifications_service, analytics_service, log_service
- Permite o arhitectură decuplată și extensibilă
- Asigură comunicare asincronă între servicii

### Microservicii (Nivel 1)

| Serviciu | Rol Principal | Responsabilități |
|----------|---------------|------------------|
| **auth_service** | Autentificare | JWT, OAuth, 2FA, validare token |
| **business_service** | Gestionare afaceri | Puncte de lucru, abonamente, profil afacere |
| **orders_service** | Gestionare comenzi | Rezervări, statusuri, istoric |
| **notifications_service** | Comunicare | Email/SMS, notificări push |
| **payments_service** | Procesare plăți | Integrare Netopia, reconciliere |

Fiecare microserviciu are propria bază de date PostgreSQL, izolând datele și evitând dependențele directe.

### Microservicii (Nivel 2 - Extensie și Scalare)

| Serviciu | Funcționalitate |
|----------|-----------------|
| **users_service** | Profiluri, adrese, preferințe |
| **location_service** | IP2Location, geo-fencing, hartă |
| **analytics_service** | Statistici, KPI-uri, heatmaps |
| **event_router** | Centralizează/loghează evenimente RabbitMQ |
| **search_service** | Indexare/filtrare rapidă |
| **log_service** | Audit trail, observabilitate |

## Detalii Implementare bee_auth_service

### Scopul Serviciului

`bee_auth_service` este microserviciul responsabil de:
- Înregistrare și autentificare utilizatori
- Emitere și validare token-uri JWT
- Integrare cu provideri OAuth (Google, Facebook)
- Implementare 2FA (autentificare în doi factori)
- Gestionare roluri și permisiuni

### Modelul de Date Principal

```python
import uuid
from datetime import datetime
from enum import Enum

class UserRole(Enum):
    CLIENT = "client"
    ADMIN_BUSINESS = "admin_business"
    COURIER = "courier"
    COLLABORATOR = "collaborator"
    SUPERADMIN = "superadmin"

class User:
    id: uuid.UUID
    email: str
    hashed_password: str
    full_name: str
    phone_number: str  # Pentru 2FA
    role: UserRole
    is_active: bool
    is_email_verified: bool
    is_social: bool
    provider: str  # google, facebook, etc.
    social_id: str
    avatar_url: str
    created_at: datetime
    updated_at: datetime
```

Tabele adiționale:
- `login_attempts` - pentru prevenirea atacurilor brute-force
- `email_verification` - pentru validarea adreselor de email
- `twofa_tokens` - pentru gestionarea codurilor 2FA

### Fluxuri de Autentificare

#### 1. Înregistrare Utilizator
- Endpoint: `POST /register`
- Validări: email unic, parolă puternică, telefon valid
- Generare token verificare email
- Emitere eveniment RabbitMQ: `user.registered`

#### 2. Autentificare Clasică
- Endpoint: `POST /login`
- Verificare credențiale
- Înregistrare tentativă login (IP, user-agent)
- Emitere JWT
- Eveniment RabbitMQ: `user.logged_in`

#### 3. Autentificare Socială
- Flow: `GET /auth/social/login?provider=google`
- Callback OAuth
- Creare/actualizare cont utilizator
- Emitere JWT

#### 4. Validare Token pentru alte Microservicii
- Endpoint: `GET /validate`
- Verificare semnătură JWT
- Returnare informații utilizator (id, email, rol)

### Securitate Implementată

- Hashing parole cu bcrypt
- Rate limiting pe endpoint-uri sensibile
- Protecție brute-force prin monitorizarea tentativelor eșuate
- Expirare token-uri (JWT: 2 ore, Email: 15 minute, 2FA: 5 minute)
- Logging complet pentru audit

### Comunicare cu alte Microservicii

#### Evenimente Emise (RabbitMQ)
- `user.registered` - la înregistrare nouă
- `user.logged_in` - la autentificare reușită
- `user.2fa_requested` - când se cere cod 2FA
- `user.email_verification_sent` - la trimitere email verificare

#### Consumatori Tipici
- `notifications_service` - pentru trimitere email-uri/SMS-uri
- `analytics_service` - pentru statistici de utilizare
- `log_service` - pentru audit trail

## Tipuri de Utilizatori și Roluri

| Rol | Permisiuni Principale |
|-----|------------------------|
| **Client** | Vizualizare afaceri, comenzi, rezervări, recenzii, hartă, chat |
| **Administrator afacere** | Gestionare pagină, program, comenzi, statistici |
| **Livrator** | Acceptă/refuză livrări, chat, hartă |
| **Colaborator zonal** | Adaugă afaceri, urmărește comisioane |
| **Superadmin** | Control complet, statistici, moderare, setări globale |

## Observabilitate și Monitorizare

Serviciul expune:
- Metrici Prometheus pentru monitorizare
- Logging structurat în format JSON
- Tracing pentru cereri între servicii

## Dezvoltare și Testare

### Dezvoltare Locală
```bash
# Instalare dependențe
poetry install

# Rulare server dezvoltare
poetry run uvicorn main:app --reload
```

### Testare
```bash
# Rulare teste
poetry run pytest

# Verificare acoperire cod
poetry run pytest --cov=bee_auth_service
```

### Docker
```bash
# Construire imagine
docker build -t bee-auth-service .

# Rulare container
docker run -p 8000:8000 bee-auth-service
```

## Integrare în Ecosistemul BeeConect

### Exemplu de Flux Complet
1. Utilizatorul se înregistrează prin `auth_service`
2. `notifications_service` primește evenimentul și trimite email de confirmare
3. După confirmare, utilizatorul se poate autentifica
4. Cu token-ul JWT, poate accesa `business_service` pentru a vedea afaceri
5. Poate plasa o comandă prin `orders_service`
6. `payments_service` procesează plata
7. `notifications_service` trimite confirmarea comenzii

## Planuri de Dezvoltare Viitoare

### Etape Planificate
1. ✅ Creare `auth_service` - MVP complet + UI simplu + testare Docker
2. 🔜 Creare `business_service` + legare la `auth_service` (validare token)
3. 🔜 Adăugare RabbitMQ + `notifications_service`
4. 🔜 Integrare plăți + dashboard UI
5. 🔜 Consolidare cu API Gateway și CI/CD

## Troubleshooting

### Probleme Comune și Soluții
- **Eroare la validare token**: Verificați dacă SECRET_KEY este consistentă între servicii
- **RabbitMQ connection refused**: Verificați dacă serviciul RabbitMQ rulează
- **Rate limiting prea restrictiv**: Ajustați limitele în configurație

## Resurse Adiționale

- Documentație FastAPI: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- Documentație RabbitMQ: [https://www.rabbitmq.com/documentation.html](https://www.rabbitmq.com/documentation.html)
- Documentație Docker: [https://docs.docker.com/](https://docs.docker.com/)