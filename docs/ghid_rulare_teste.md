# Ghid pentru Rularea Testelor - BeeConect Authentication Service

Acest document explică cum să configurați și să rulați testele pentru serviciul de autentificare BeeConect.

## Cerințe preliminare

Înainte de a rula testele, asigurați-vă că aveți următoarele:

1. Python 3.12 sau o versiune mai nouă instalată
2. Poetry instalat pentru gestionarea dependențelor
3. Codul sursă al proiectului clonat pe mașina locală

## Configurarea mediului de testare

### 1. Instalarea dependențelor

Folosiți Poetry pentru a instala toate dependențele necesare, inclusiv cele pentru dezvoltare:

```bash
poetry install
```

Acest lucru va instala toate dependențele definite în `pyproject.toml`, inclusiv pachetele necesare pentru testare precum pytest, httpx și fakeredis.

### 2. Activarea mediului virtual

Activați mediul virtual creat de Poetry:

```bash
poetry shell
```

## Rularea testelor

### Rularea tuturor testelor

Pentru a rula toate testele din directorul `tests/`:

```bash
pytest
```

sau

```bash
python -m pytest
```

### Rularea testelor specifice

Pentru a rula un fișier de test specific:

```bash
pytest tests/test_auth_login.py
```

Pentru a rula un test specific dintr-un fișier:

```bash
pytest tests/test_auth_login.py::test_login_success_records_attempt_and_returns_jwt
```

### Rularea testelor cu afișarea detaliilor

Pentru a vedea mai multe detalii în timpul rulării testelor:

```bash
pytest -v
```

Pentru a vedea detalii foarte amănunțite:

```bash
pytest -vv
```

### Rularea testelor cu afișarea output-ului

Pentru a afișa output-ul testelor (print statements):

```bash
pytest -s
```

## Raportarea acoperirii testelor

Pentru a genera un raport de acoperire a testelor, aveți nevoie de pachetul `pytest-cov`:

```bash
poetry add --dev pytest-cov
```

Apoi puteți rula testele cu generarea raportului de acoperire:

```bash
pytest --cov=.
```

Pentru un raport mai detaliat:

```bash
pytest --cov=. --cov-report=html
```

Acest lucru va genera un raport HTML în directorul `htmlcov/`. Deschideți fișierul `index.html` din acest director pentru a vizualiza raportul.

## Testarea componentelor specifice

### Testarea autentificării

```bash
pytest tests/test_auth_login.py tests/test_auth_register.py
```

### Testarea verificării e-mailului

```bash
pytest tests/test_verify_email.py
```

### Testarea autentificării în doi pași

```bash
pytest tests/test_twofa_flow.py tests/test_verify_2fa.py
```

### Testarea securității

```bash
pytest tests/test_security_headers.py tests/test_cors.py
```

### Testarea evenimentelor

```bash
pytest tests/test_events.py
```

## Depanarea testelor

### Testele eșuează din cauza dependențelor

Dacă testele eșuează din cauza dependențelor lipsă, asigurați-vă că ați instalat toate dependențele de dezvoltare:

```bash
poetry install --with dev
```

### Testele eșuează din cauza configurării

Unele teste pot necesita variabile de mediu specifice. Creați un fișier `.env.test` în directorul rădăcină al proiectului și adăugați variabilele necesare:

```
DATABASE_URL=sqlite:///:memory:
SECRET_KEY=test_secret_key
ENVIRONMENT=test
```

### Testele sunt lente

Pentru a rula testele mai rapid, puteți utiliza opțiunea `-xvs`:

```bash
pytest -xvs
```

Aceasta va opri testarea la primul eșec (`-x`), va afișa detalii (`-v`) și va afișa output-ul (`-s`).

## Integrarea testelor în CI/CD

Testele sunt configurate pentru a rula automat în pipeline-ul CI/CD. Configurația se găsește în fișierele de configurare CI/CD ale proiectului.

## Concluzie

Rularea regulată a testelor este esențială pentru menținerea calității și stabilității serviciului de autentificare BeeConect. Asigurați-vă că rulați testele înainte de a trimite modificări și că adăugați teste noi pentru orice funcționalitate nouă implementată.