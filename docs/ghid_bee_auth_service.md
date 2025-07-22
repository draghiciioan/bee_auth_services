# Ghid Bee Auth Service

## Pentru utilizatori non-tehnici
Bee Auth Service este serviciul care gestionează conturile din platforma BeeConect. Cu ajutorul lui îți poți crea rapid un cont, te poți autentifica în siguranță și îți poți păstra datele protejate.

### Creare cont
1. Accesează formularul de înregistrare din aplicație sau trimită o solicitare către endpoint-ul `/register`.
2. Vei primi un email de confirmare pentru validarea adresei.
3. După confirmare, te poți autentifica folosind email și parolă sau prin contul tău de Google/Facebook.

### Beneficii
- Ai un singur cont pentru toate serviciile BeeConect.
- Poți vedea istoricul comenzilor și preferințelor tale.
- Datele sunt securizate prin parole criptate și autentificare în doi pași.

## Pentru dezvoltatori
### Instalare și configurare
```bash
poetry install
poetry run uvicorn main:app --reload
```

Setează variabilele de mediu esențiale:
- `DATABASE_URL` – conexiunea la PostgreSQL
- `SECRET_KEY` – cheia de semnare JWT
- `RABBITMQ_URL` – adresa serverului RabbitMQ

### Rulare teste
```bash
poetry run pytest
```

### Endpoint-uri principale
- `POST /register`
- `POST /login`
- `GET /validate`
- `POST /request-reset`
- `POST /reset-password`

### Detalii RabbitMQ
Evenimentele sunt publicate pe exchange-ul `bee.auth.events` cu routing key-uri precum `user.registered` și `user.logged_in`. Consumatorii se pot abona pentru a reacționa la aceste acțiuni.

### Exemplu de flux
1. Utilizatorul trimite datele la `/register`.
2. Serviciul creează contul și publică `user.registered`.
3. Un consumator trimite emailul de confirmare.
4. La autentificare, `user.logged_in` este emis pentru monitorizare.
5. Pentru recuperare parolă, utilizatorul apelează `/request-reset`.
6. Consumatorul trimite link-ul cu tokenul de resetare.
7. Utilizatorul trimite noua parolă la `/reset-password` împreună cu tokenul.

## Pentru un agent AI
Un agent poate interoga direct API-ul pentru a automatiza procese de testare sau suport.

### Interogarea endpoint-urilor
- Înregistrare:
  ```bash
  curl -X POST <url>/register -d '{"email":"test@example.com","password":"Secret123"}' -H 'Content-Type: application/json'
  ```
- Autentificare:
  ```bash
  curl -X POST <url>/login -d '{"email":"test@example.com","password":"Secret123"}' -H 'Content-Type: application/json'
  ```
- Validare token:
  ```bash
  curl -H "Authorization: Bearer <token>" <url>/validate
  ```

### Resetare parolă
- Solicitare resetare:
  ```bash
  curl -X POST <url>/request-reset -d '{"email":"user@example.com"}' -H 'Content-Type: application/json'
  ```
- Schimbare parolă:
  ```bash
  curl -X POST <url>/reset-password -d '{"token":"<token>","new_password":"NewPass1!"}' -H 'Content-Type: application/json'
  ```

### Structura evenimentelor RabbitMQ
```json
{
  "event_id": "<uuid>",
  "timestamp": "<iso8601>",
  "user_id": "<uuid>",
  "email": "user@example.com",
  "event": "user.registered"
}
```

### Logare și monitorizare
Logurile sunt emise în format JSON și pot fi urmărite prin stack-ul ELK sau Loki. Metricile Prometheus expun contorul `bee_auth_errors_total` pentru detectarea rapidă a erorilor.
