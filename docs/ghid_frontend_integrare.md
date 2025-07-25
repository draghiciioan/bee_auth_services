# Ghid Integrare Front-end BeeConect

Acest document descrie pe scurt fluxurile de bază pe care aplicațiile web sau mobile trebuie să le implementeze pentru a utiliza serviciul de autentificare.

## 1. Înregistrare

```
[Formular] --POST--> /v1/auth/register --> [Backend] --email--> Utilizator
```
1. Utilizatorul completează formularul de înregistrare.
2. Se trimite o cerere `POST /v1/auth/register`.
3. Backend-ul creează contul și generează un token de confirmare.
4. Utilizatorul primește un email cu link-ul de confirmare.

## 2. Confirmare email

```
Utilizator --GET--> /v1/auth/verify-email?token=... --> [Cont activat]
```
După accesarea link-ului, contul este marcat ca verificat.

## 3. Autentificare

```
[Formular] --POST--> /v1/auth/login --> [Backend]
          ↳ JWT                             ↳ 2FA necesar
```
- Pentru conturile fără 2FA, răspunsul conține direct tokenul JWT.
- Dacă este activă autentificarea în doi pași, backend-ul răspunde cu `{"message": "2fa_required", "twofa_token": "..."}`.

### Verificare 2FA

```
Utilizator --POST--> /v1/auth/verify-2fa (twofa_token + totp_code) --> JWT
```
După introducerea codului, se emite tokenul de acces.

## 4. Resetare parolă

```
[Formular email] --POST--> /v1/auth/request-reset --> [Email cu token]
[Formular reset] --POST--> /v1/auth/reset-password --> Parolă actualizată
```
1. Utilizatorul solicită resetarea parolei prin `POST /v1/auth/request-reset`.
2. După primirea emailului, trimite noua parolă la `POST /v1/auth/reset-password`.
