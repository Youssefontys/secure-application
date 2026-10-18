# Week 6: Logging en monitoring

De app logt nu elke security-gebeurtenis als één JSON-regel (MIT-31): wanneer, wat, vanaf welk adres en, als dat bekend is, van welk account. Dat gebeurt op de plekken waar de app al beslist. Een aanval laat daardoor een spoor na (MC-28), lokaal en op Azure op dezelfde manier. Wachtwoorden, codes en geheimen komen er nooit in.

De details staan in de entries (MC-28, MIT-31; A-11, C-05 en F-05 in de architectuur) en de tests (T-93, T-94, T-100 tot T-102, T-104, T-107, T-108). Sinds c4ce459 geeft een blokkade op Azure ook een mail (MIT-37). Overgenomen uit BOK-SECENGINEER, dat dit al deed; de audit van 18-10-2026 maakte twee dingen strakker: een naam alleen als het account bestaat, en één regel per blokkade.

## De dreiging

- **Iedereen die iets probeert**, van wachtwoorden raden (MC-03) tot rijen in de database wijzigen (MC-08, MC-23), deed dat tot nu toe zonder spoor. De blokkades werkten wel, maar niemand zag ze.
- **Achteraf** viel niet na te gaan wie wanneer vanaf welk adres wat had gedaan.
- **De log zelf** is ook een doel: wie hem kan vervalsen, legt een vals spoor. Een gebruikersnaam met een regeleinde had een valse regel kunnen maken (MC-26).

## Wat er beter wordt

| Onderdeel | Voor | Na |
|---|---|---|
| Een kleine aanval: zes foute wachtwoorden, een onbekende naam, een formulier zonder CSRF-token | De log was leeg | Acht regels: vijf mislukte logins, de blokkade, de onbekende naam en het geweigerde token |
| Soorten gebeurtenissen | Alleen onverwachte fouten (MIT-25) | 21 soorten, op elke plek waar de app beslist |
| Een wachtwoord per ongeluk in het naamveld | Stond leesbaar in de log, want het voldeed aan de naamregel | Niet in de log: een naam alleen als het account bestaat |
| 40 pogingen tijdens een blokkade | 41 regels, één per geweigerde poging | Eén regel per blokkade (`lockout_started`) |
| De log op Azure | Alleen live te volgen; na een herstart weg | 30 dagen in Log Analytics, waar de app niet bij kan (uitgerold op 18-10-2026) |
| Een naam met een regeleinde | Kwam niet in de log, want er werd niets gelogd | Komt er nog steeds niet in: alleen de naam van een bestaand account, en JSON escapet stuurtekens |

## Hoe het werkt

- **Eén functie:** `events.event(soort, velden)` in `app/events.py`. Hij voegt zelf de tijd (UTC), het IP-adres en het account toe, als er iemand is ingelogd. Velden zonder waarde blijven weg.
- **Het formaat:** één JSON-regel per gebeurtenis, bijvoorbeeld:

  ```
  {"time": "2026-10-17T23:05:48+00:00", "event": "lockout_started", "ip": "172.18.0.1", "scope": "password_account_ip", "minutes": 15}
  ```

- **De plek:** stderr van de container. Lokaal is dat `docker compose logs app`; op Azure zet Container Apps hem in Log Analytics, in de tabel `ContainerAppConsoleLogs_CL` (de regel staat in `Log_s`). De code is op beide hetzelfde. De output `security_log_command` van Terraform geeft de blokkades van de laatste dag.
- **Een gebruikersnaam** komt er alleen in als het account bestaat (`target()`); anders staat er `"known": false`. Wat iemand in het naamveld typt, ook een wachtwoord, blijft zo buiten de log.
- **Een blokkade** logt zichzelf één keer, op het moment dat hij begint: `lockout_started` in `throttle.attempt()`, met de soort teller (`scope`) en hoe lang.
- **Een mail bij een blokkade (MIT-37):** op Azure kijkt een alert elke 5 minuten of er een `lockout_started` in Log Analytics staat, en mailt dan de beheerder. Na een mail is de regel een uur stil. Hij leest met een eigen identiteit, met alleen leesrechten op de workspace.

| Soort | Wanneer | Extra velden | Misuse case |
|---|---|---|---|
| `account_created`, `register_taken` | Registreren: gelukt, naam bezet | naam | MC-09, MC-10 |
| `login_failed`, `login_ok` | Inloggen met het wachtwoord, en na de code | account en naam, of `known: false`; `with_2fa` | MC-03, MC-18 |
| `totp_failed` | Een foute code | account | MC-15 |
| `recovery_failed`, `recovery_used` | Inloggen met de herstelcode | account | MC-19 |
| `forgot_failed`, `password_reset` | Wachtwoord vergeten | account en naam, of `known: false` | MC-21 |
| `recovery_code_new`, `twofa_enabled`, `twofa_reset` | Tweestapsverificatie aan, opnieuw, nieuwe herstelcode | account | MC-20 |
| `reauth_failed`, `password_changed`, `account_deleted` | Het huidige wachtwoord bij wijzigen of verwijderen | account | MC-12, MC-13 |
| `lockout_started` | Een teller gaat op slot: registreren, wachtwoord, code, herstelcode of herauthenticatie | soort teller, minuten | MC-03, MC-10, MC-15, MC-18, MC-19 |
| `logout`, `session_rejected` | Uitloggen, of een cookie met een oude sessieversie | account | MC-04 |
| `csrf_refused` | Een POST zonder het juiste token | de route | MC-05 |
| `note_limit`, `note_unreadable` | 25 notities bereikt; een notitie die niet ontsleutelt | account, notitie | MC-10, MC-08, MC-23 |

## Waarom het veilig is

| Wat | Hoe | Gemeten |
|---|---|---|
| Elke soort komt echt voor | De test haalt alle soorten uit de code en zoekt ze in de log van een volledige run | T-93 |
| Wanneer, waar, wie, wat | Tijd, adres, account en soort in elke regel, zoals de OWASP Logging Cheat Sheet vraagt | T-93 |
| Geen geheimen in de log | De test zoekt de testwachtwoorden, TOTP-geheimen en herstelcodes in de log: geen enkele | T-94 |
| Geen valse regels | JSON escapet regeleindes; een naam zonder account wordt niet gelogd | T-94 |
| Geen wachtwoord via het naamveld | Een naam alleen als het account bestaat | T-100 |
| Een script vult de log niet | Eén regel per blokkade, niet per geweigerde poging | T-101 |
| Iemand ziet een blokkade | Binnen een paar minuten een mail, via een alert op `lockout_started` | T-107; de mail zelf T-108 |

## Persoonsgegevens

Een IP-adres en een gebruikersnaam zijn persoonsgegevens (A-11). Daarom:
- staat er alleen in wat voor het spoor nodig is: geen notities, geen wachtwoord, geen sessiecookie;
- hoort er een bewaartermijn bij: op Azure 30 dagen, en dan echt weg. Zonder `immediate_data_purge_on_30_days_enabled` kan het 31 dagen worden, zegt Microsoft.
- hoort er een doel bij; dat komt bij de AVG-stap. De OWASP Logging Cheat Sheet noemt ook pseudonimiseren als mogelijkheid.

## Lokaal en op Azure

- **Lokaal** bewaart Docker de log zolang de container bestaat. Een `docker compose down` of een nieuwe build begint met een lege log.
- **Op Azure** zet Container Apps de log in een Log Analytics-workspace (`terraform/logs.tf`, sinds d547182): 30 dagen, met een rem van 0,1 GB per dag. Een regel staat er een paar minuten na het gebeuren; live meekijken kan nog steeds met de log stream. Gemeten na de uitrol op 18-10-2026: een geweigerd CSRF-token stond erin, met het adres van de bezoeker en niet dat van de proxy (T-102, T-104). Opvragen kan met de output `security_log_command`; de eerste keer vraagt `az` om de extensie log-analytics te installeren.
- **De databaselog** gaat nog nergens heen: de drie Trivy-punten daarover (AZU-0019, AZU-0021, AZU-0024) staan nog open.

## Wat het niet oplost

- **Alleen een blokkade geeft een mail.** Een reeks mislukte logins verspreid over veel adressen, die nergens een teller op slot zet, geeft geen melding; dat kan een tweede regel worden, zoals BOK-SECENGINEER deed met `threshold_crossed`. De mail komt een paar minuten later, niet direct.
- **Lokaal kan wie de host beheert de log wissen.** Op Azure niet vanuit de app: de identiteit van de app heeft geen rechten op de workspace.
- **De rem van 0,1 GB per dag kan het spoor stoppen.** Is hij bereikt, dan verzamelt Log Analytics niets meer tot de volgende dag, en wat er toch nog binnenkomt, wordt betaald. Microsoft noemt de rem een vangnet tegen onverwachte pieken, geen filter. Wie hem met een script haalt, valt daarna niet meer op.
- **Gewone verzoeken worden niet gelogd.** Gunicorn draait zonder access-log; daarmee blijven ook de healthchecks van elke 5 seconden buiten de log.
- **Geen `observe`-stand.** BOK-SECENGINEER kon de IP-limieten alleen laten melden in plaats van blokkeren. Hier blokkeren ze altijd; de log laat nu wel zien wat er geblokkeerd is.

## Keuzes

- **stderr, geen bestand.** Een bestand in de container is weg met de container, en op Azure leest Container Apps stderr. Zo is lokaal gelijk aan Azure.
- **Log Analytics als bestemming.** Het is de standaard van Container Apps, en de enige waarbij de query-editor in de portal werkt. Azure Monitor als bestemming vraagt nog diagnostic settings, voor hier hetzelfde resultaat.
- **30 dagen.** Daarvan zitten er 31 in de prijs, dus korter scheelt niets en langer kost extra. Lang genoeg om een aanval achteraf terug te zien, en niet langer dan nodig voor persoonsgegevens.
- **JSON, niet vrije tekst.** Elk veld is apart te zoeken, en JSON escapet wat een aanvaller in een veld stopt.
- **Op de plekken waar de app al beslist.** Geen aparte laag die raadt wat er gebeurde; de route die weigert, logt ook waarom.
- **Een naam alleen als het account bestaat.** Zo zie je bij een aanval wie het doelwit was. Eerst gold de naamregel, maar een wachtwoord als `Zomervakantie2026` voldoet daar ook aan; dat liet de audit van 18-10-2026 zien.
- **Een blokkade één keer loggen.** Elke geweigerde poging loggen gaf een script de kans de log te vullen: lokaal roteert de echte aanval er dan uit, op Azure loopt de rekening op. Het begin van de blokkade is het signaal; hoe vaak het daarna nog geprobeerd werd, zie je niet.
- **Een mail van Azure Monitor, niet van de app.** Echt direct kan alleen als de app zelf mailt; dan heeft de app een mailtoken nodig, en wie de app overneemt, kan de seintjes uitzetten. De regel kijkt elke 5 minuten (€1,32 per maand, volgens de prijs-API van Azure); elke minuut kost €2,64 en scheelt weinig, want een regel staat pas na een paar minuten in Log Analytics.
- **Het adres niet in de repo.** `setup.py azure` stelt het adres van `az login` voor en geeft het alleen aan Terraform mee; het staat in de state en in de action group, niet in git (A-13).
- **Geen sessie-ID.** OWASP raadt af de sessie zelf te loggen. De sessiecookie van Flask is bovendien geen ID maar de hele sessie, en die komt er nooit in.

## Screenshots

Voor het verslag, lokaal in `screenshots/Week 6 Logging/` (niet in de repo).

| Onderdeel | Voor | Na | Code |
|---|---|---|---|
| Security-events | `week6_voor_logging_1_geen_spoor` | `week6_na_logging_1_json_per_gebeurtenis` | `week6_code_logging_1_events` |
| Wachtwoord in het naamveld | `week6_voor_logging_2_wachtwoord_in_log` | `week6_na_logging_2_alleen_bestaande_namen` | `week6_code_logging_1_events` |
| Een regel per blokkade | `week6_voor_logging_3_regel_per_poging` | `week6_na_logging_3_een_regel_per_blokkade` | `week6_code_logging_1_events` |
| De log op Azure | n.v.t. (eerste uitrol) | `week6_na_logging_4_azure` | `week6_code_logging_2_azure` |
| Een mail bij een blokkade | `week6_voor_logging_5_geen_alert` | `week6_na_logging_5_alert` | `week6_code_logging_3_alert` |

## Bronnen

Opgehaald en gecontroleerd op 17-10-2026; de pagina's van Microsoft op 18-10-2026.

- OWASP Logging Cheat Sheet ("when, where, who and what", geen wachtwoorden, sanitizen tegen log injection, bewaartermijn): https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- OWASP Session Management Cheat Sheet (geen sessie-ID in de log): https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- Microsoft, log-opties van Container Apps (log-analytics, azure-monitor of none; zonder bewaren alleen de log stream): https://learn.microsoft.com/en-us/azure/container-apps/log-options
- Microsoft, logs van Container Apps in Log Analytics (tabel `ContainerAppConsoleLogs_CL`, kolom `Log_s`): https://learn.microsoft.com/en-us/azure/container-apps/log-monitoring
- Microsoft, bewaartermijn (standaard 30 dagen, 31 in de prijs, `immediatePurgeDataOn30Days`): https://learn.microsoft.com/en-us/azure/azure-monitor/logs/data-retention-configure
- Microsoft, dagelijkse rem (een vangnet, geen filter; daarna niets verzameld tot de volgende dag): https://learn.microsoft.com/en-us/azure/azure-monitor/logs/daily-cap
- Microsoft, log search alert rules (een eigen identiteit; zonder leest de regel met de rechten van wie hem het laatst wijzigde): https://learn.microsoft.com/en-us/azure/azure-monitor/alerts/alerts-create-log-alert-rule
- Azure Retail Prices API (Azure Monitor, France Central: een log-alert elke 5 minuten €1,32 per maand, elke minuut €2,64): https://prices.azure.com/api/retail/prices
