# Week 6: Logging en monitoring

De app logt nu elke security-gebeurtenis als één JSON-regel (MIT-31): wanneer, wat, vanaf welk adres en, als dat bekend is, van welk account. Dat gebeurt op de plekken waar de app al beslist. Een aanval laat daardoor een spoor na (MC-28), lokaal en op Azure op dezelfde manier. Wachtwoorden, codes en geheimen komen er nooit in.

De details staan in de entries (MC-28, MIT-31; A-11, C-05 en F-05 in de architectuur) en de tests (T-93, T-94). Overgenomen uit BOK-SECENGINEER, dat dit al deed.

## De dreiging

- **Iedereen die iets probeert**, van wachtwoorden raden (MC-03) tot rijen in de database wijzigen (MC-08, MC-23), deed dat tot nu toe zonder spoor. De blokkades werkten wel, maar niemand zag ze.
- **Achteraf** viel niet na te gaan wie wanneer vanaf welk adres wat had gedaan.
- **De log zelf** is ook een doel: wie hem kan vervalsen, legt een vals spoor. Een gebruikersnaam met een regeleinde had een valse regel kunnen maken (MC-26).

## Wat er beter wordt

| Onderdeel | Voor | Na |
|---|---|---|
| Een kleine aanval: zes foute wachtwoorden, een onbekende naam, een formulier zonder CSRF-token | De log was leeg | Acht regels: vijf mislukte logins, de blokkade, de onbekende naam en het geweigerde token |
| Soorten gebeurtenissen | Alleen onverwachte fouten (MIT-25) | 26 soorten, op elke plek waar de app beslist |
| Een naam met een regeleinde | Kwam niet in de log, want er werd niets gelogd | Komt er nog steeds niet in: alleen een geldige naam, en JSON escapet stuurtekens |

## Hoe het werkt

- **Eén functie:** `events.event(soort, velden)` in `app/events.py`. Hij voegt zelf de tijd (UTC), het IP-adres en het account toe, als er iemand is ingelogd. Velden zonder waarde blijven weg.
- **Het formaat:** één JSON-regel per gebeurtenis, bijvoorbeeld:

  ```
  {"time": "2026-10-17T17:40:37+00:00", "event": "login_blocked", "ip": "172.18.0.1", "username": "laura", "minutes": 15}
  ```

- **De plek:** stderr van de container. Lokaal is dat `docker compose logs app`, op Azure de log van Container Apps. De code is op beide hetzelfde.
- **Een getypte gebruikersnaam** komt er alleen in als hij aan de naamregel van MIT-22 voldoet (`logged_name()`). Wat een aanval verder intypt, blijft buiten de log.

| Soort | Wanneer | Extra velden | Misuse case |
|---|---|---|---|
| `account_created`, `register_taken`, `register_blocked` | Registreren: gelukt, naam bezet, limiet | naam, minuten | MC-09, MC-10 |
| `login_failed`, `login_blocked`, `login_ok` | Inloggen met het wachtwoord, en na de code | naam, account, minuten, `with_2fa` | MC-03, MC-18 |
| `totp_failed`, `totp_blocked` | Een foute code, of op slot | account, minuten | MC-15 |
| `recovery_failed`, `recovery_blocked`, `recovery_used` | Inloggen met de herstelcode | account, minuten | MC-19 |
| `forgot_failed`, `forgot_blocked`, `password_reset` | Wachtwoord vergeten | naam, account, minuten | MC-21 |
| `recovery_code_new`, `twofa_enabled`, `twofa_reset` | Tweestapsverificatie aan, opnieuw, nieuwe herstelcode | account | MC-20 |
| `reauth_failed`, `reauth_blocked`, `password_changed`, `account_deleted` | Het huidige wachtwoord bij wijzigen of verwijderen | account, minuten | MC-12, MC-13 |
| `logout`, `session_rejected` | Uitloggen, of een cookie met een oude sessieversie | account | MC-04 |
| `csrf_refused` | Een POST zonder het juiste token | de route | MC-05 |
| `note_limit`, `note_unreadable` | 25 notities bereikt; een notitie die niet ontsleutelt | account, notitie | MC-10, MC-08, MC-23 |

## Waarom het veilig is

| Wat | Hoe | Gemeten |
|---|---|---|
| Elke soort komt echt voor | De test haalt alle soorten uit de code en zoekt ze in de log van een volledige run | T-93 |
| Wanneer, waar, wie, wat | Tijd, adres, account en soort in elke regel, zoals de OWASP Logging Cheat Sheet vraagt | T-93 |
| Geen geheimen in de log | De test zoekt de testwachtwoorden, TOTP-geheimen en herstelcodes in de log: geen enkele | T-94 |
| Geen valse regels | JSON escapet regeleindes; een ongeldige naam wordt niet gelogd | T-94 |

## Persoonsgegevens

Een IP-adres en een gebruikersnaam zijn persoonsgegevens (A-11). Daarom:
- staat er alleen in wat voor het spoor nodig is: geen notities, geen wachtwoord, geen sessiecookie;
- hoort er een doel en een bewaartermijn bij. Die komen bij de AVG-stap; de OWASP Logging Cheat Sheet noemt ook pseudonimiseren als mogelijkheid.

## Lokaal en op Azure

- **Lokaal** bewaart Docker de log zolang de container bestaat. Een `docker compose down` of een nieuwe build begint met een lege log.
- **Op Azure** staat de log voorlopig alleen live in Container Apps. Bewaren, met een termijn, kan met een Log Analytics-workspace in Terraform; dat hoort bij de uitrol, samen met de drie Trivy-punten over de databaselog (AZU-0019, AZU-0021, AZU-0024).

## Wat het niet oplost

- **Niemand kijkt mee.** Er zijn geen meldingen (alerts) bij een blokkade of een reeks mislukte logins.
- **Wie de host of de container beheert, kan de log wissen.** Een log die de app zelf niet meer kan veranderen, vraagt een aparte plek, zoals Log Analytics op Azure.
- **Gewone verzoeken worden niet gelogd.** Gunicorn draait zonder access-log; daarmee blijven ook de healthchecks van elke 5 seconden buiten de log.
- **Geen `observe`-stand.** BOK-SECENGINEER kon de IP-limieten alleen laten melden in plaats van blokkeren. Hier blokkeren ze altijd; de log laat nu wel zien wat er geblokkeerd is.

## Keuzes

- **stderr, geen bestand.** Een bestand in de container is weg met de container, en op Azure leest Container Apps stderr. Zo is lokaal gelijk aan Azure.
- **JSON, niet vrije tekst.** Elk veld is apart te zoeken, en JSON escapet wat een aanvaller in een veld stopt.
- **Op de plekken waar de app al beslist.** Geen aparte laag die raadt wat er gebeurde; de route die weigert, logt ook waarom.
- **Een naam alleen als hij geldig is.** Zo zie je bij een aanval op een bestaande naam wel wie het doelwit was, maar komt rommel er niet in.
- **Geen sessie-ID.** OWASP raadt af de sessie zelf te loggen. De sessiecookie van Flask is bovendien geen ID maar de hele sessie, en die komt er nooit in.

## Screenshots

Voor het verslag, lokaal in `screenshots/Week 6 Logging/` (niet in de repo).

| Onderdeel | Voor | Na | Code |
|---|---|---|---|
| Security-events | `week6_voor_logging_1_geen_spoor` | `week6_na_logging_1_json_per_gebeurtenis` | `week6_code_logging_1_events` |

## Bronnen

Opgehaald en gecontroleerd op 17-10-2026.

- OWASP Logging Cheat Sheet ("when, where, who and what", geen wachtwoorden, sanitizen tegen log injection, bewaartermijn): https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- OWASP Session Management Cheat Sheet (geen sessie-ID in de log): https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
