# Bidragsguide

Takk for at du vurderer å bidra til OSINT Email Investigator! Dette dokumentet gir retningslinjer for hvordan du kan bidra til prosjektet.

## Innholdsfortegnelse

- [Code of Conduct](#code-of-conduct)
- [Hvordan kan jeg bidra?](#hvordan-kan-jeg-bidra)
- [Utviklingsmiljø](#utviklingsmiljø)
- [Pull Requests](#pull-requests)
- [Kodestil](#kodestil)
- [Testing](#testing)
- [Dokumentasjon](#dokumentasjon)

## Code of Conduct

Dette prosjektet følger en Code of Conduct som alle bidragsytere må følge. Ved å delta forplikter du deg til å opprettholde denne koden.

## Hvordan kan jeg bidra?

### Rapportere Bugs

- Sjekk først om buggen allerede er rapportert
- Bruk bug report templaten
- Inkluder så mange detaljer som mulig
- Legg ved skjermbilder hvis relevant

### Foreslå Forbedringer

- Sjekk eksisterende forslag først
- Beskriv problemet og løsningen
- Forklar hvorfor dette er nyttig
- Diskuter implementasjonsdetaljer

### Pull Requests

1. Fork repositoriet
2. Opprett en branch fra `main`
3. Implementer endringene
4. Skriv/oppdater tester
5. Oppdater dokumentasjon
6. Submit PR med detaljert beskrivelse

## Utviklingsmiljø

1. Klon repositoriet:
```bash
git clone git@github.com:yourusername/OSINT_epost_etterforsker.git
cd OSINT_epost_etterforsker
```

2. Sett opp utviklingsmiljø:
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # eller .\venv\Scripts\activate på Windows
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
```

3. Start utviklingsservere:
```bash
# Backend
cd backend
uvicorn main:app --reload

# Frontend
cd frontend
npm run dev
```

## Kodestil

### Python
- Følg PEP 8
- Bruk type hints
- Maksimum linjelengde: 88 tegn
- Sorter imports med isort
- Formater kode med black

### TypeScript/JavaScript
- Følg Airbnb style guide
- Bruk TypeScript
- Formater med Prettier
- Bruk ESLint

### Commit Messages
- Følg conventional commits
- Start med type: feat, fix, docs, style, refactor, test, chore
- Holder det kort og beskrivende
- Referer til issue nummer

Eksempel:
```
feat(api): add email validation endpoint (#123)
```

## Testing

### Backend Testing
```bash
# Kjør alle tester
pytest

# Med coverage
pytest --cov=backend

# Spesifikk test
pytest tests/test_api.py -k "test_email_validation"
```

### Frontend Testing
```bash
# Unit tests
npm test

# E2E tests
npm run test:e2e

# Med coverage
npm test -- --coverage
```

## Dokumentasjon

- Hold README.md oppdatert
- Dokumenter nye features
- Oppdater API dokumentasjon
- Inkluder kodeeksempler
- Oppdater changelog

## Review Process

1. Automatiske sjekker må passere:
   - Linting
   - Type checking
   - Tests
   - Coverage

2. Code review krav:
   - Minst én godkjenning
   - Ingen blokkerende kommentarer
   - Alle automatiske sjekker passerer

3. Review checklist:
   - Kode følger stil guide
   - Tester er inkludert
   - Dokumentasjon er oppdatert
   - Ingen sikkerhetsproblemer
   - Performance er akseptabel

## Release Process

1. Version bump følger semver:
   - MAJOR versjon når du gjør inkompatible API endringer
   - MINOR versjon når du legger til funksjonalitet på en bakoverkompatibel måte
   - PATCH versjon når du gjør bakoverkompatible bugfikser

2. Release sjekkliste:
   - Changelog er oppdatert
   - Versjonsnummer er bumped
   - Tester passerer
   - Dokumentasjon er oppdatert
   - Release notes er klare

## Kontakt

- GitHub Issues for bugs og features
- Discussions for generelle spørsmål
- Security vulnerabilities: security@yourdomain.com

## Lisens

Ved å bidra til prosjektet godtar du at dine bidrag vil bli lisensiert under samme lisens som prosjektet (MIT License).