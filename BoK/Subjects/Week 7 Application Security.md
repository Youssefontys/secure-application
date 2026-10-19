# Week 7: Application Security

De app controleert nu alles wat binnenkomt, en valt veilig om als er iets misgaat:
- **Formulieren:** elk formulier draagt een CSRF-token (MIT-20).
- **Headers:** elk antwoord heeft een strikte CSP en verbiedt frames (MIT-21).
- **Invoer:** gebruikersnamen, de grootte van een verzoek en de HTTP-methode worden gecontroleerd (MIT-22).
- **Configuratie:** de configuratie wordt bij het starten gecontroleerd, met veilige standaarden (MIT-23).
- **Routes:** elke route is standaard dicht (MIT-24).
- **Fouten:** een fout geeft een korte melding, met de details alleen in de log (MIT-25).
- **Draaien:** de app draait met Gunicorn als gewone gebruiker, niet meer als root (MIT-26).
- **Database:** de app logt in met een eigen rol die alleen mag lezen en schrijven in de eigen tabellen (MIT-27).
- **Overgenomen uit BOK-SECENGINEER en de audit:** geen pagina in de cache van de browser (MIT-28), een sessie van hooguit 8 uur (MIT-29), een limiet op registreren en notities (MIT-30), `.env` alleen voor de eigenaar (MIT-32) en Dependabot (MIT-33). Security-events staan in Week 6 Logging (MIT-31).

Daarmee zijn MC-05 (CSRF) en MC-14 (root en de ontwikkelserver) dicht, de laatste twee voorwaarden voor de uitrol naar Azure. MC-08 (te veel rechten in de database) is dicht, op wat de app zelf mag na. MC-10 (overbelasten) en MC-27 (een gedeelde computer) zijn ook dicht.

De details staan in de entries (MC-04, MC-05, MC-07, MC-08, MC-10, MC-11, MC-14, MC-18, MC-22, MC-24 tot MC-27; MIT-20 tot MIT-30, MIT-32, MIT-33) en de tests (T-16, T-18, T-19, T-21, T-73 tot T-92, T-95, T-97). Dit bestand vat ze samen.

## De dreiging

- **Een andere site** laat de ingelogde gebruiker een formulier versturen (MC-05), of laadt de app onzichtbaar in een frame en laat hem klikken (MC-24).
- **Iedere bezoeker** stuurt vreemde of te grote invoer (MC-10), lokt een fout uit om details te zien of de log te vervalsen (MC-26), of vindt een route die per ongeluk open staat (MC-25).
- **Een verkeerde instelling** laat een aanvaller zelf zijn adres kiezen en zo de poginglimieten omzeilen (MC-18).
- **Wie de app overneemt,** was root in de container (MC-14) en superuser in de database (MC-08).

## Wat er beter wordt

| Onderdeel | Voor | Na |
|---|---|---|
| CSRF (MIT-20) | Een andere site maakte met één klik een notitie aan in het account van anna | 400 en geen notitie; de andere site kent het token niet |
| Clickjacking (MIT-21) | De app stond ingelogd in het frame van een andere site | De browser weigert het frame |
| Beveiligingsheaders (MIT-21) | Geen CSP, geen `X-Frame-Options`, geen `nosniff` | Op elk antwoord, ook op foutpagina's |
| Gebruikersnaam (MIT-22) | `<script>alert(1)</script>` werd een account; alleen het escapen hield het tegen | 3 tot 20 letters, cijfers of `_`; anders 400 |
| Grootte van een verzoek (MIT-22) | 5 MB werd helemaal ingelezen, en pas daarna geweigerd | Boven 16 KiB direct 413 |
| HEAD-verzoeken (MIT-22) | Drie keer HEAD telde als drie foute wachtwoorden | 200, en geen teller |
| `TRUSTED_PROXIES` (MIT-23) | Met -1 of 2 startte de app, en koos de aanvaller zijn adres | Alleen 0 of 1, anders start de app niet |
| `HTTPS_ONLY` (MIT-23) | Standaard uit: wie het vergat, stuurde de cookie over HTTP | Standaard aan; alleen `compose.yaml` zet het lokaal uit |
| Routes (MIT-24) | Elke route moest zelf `@login_required` hebben | Standaard dicht, met een vaste lijst publieke routes |
| Fouten (MIT-25) | De standaardpagina van Flask, en geen controle over de log | Een korte melding; de fout in de log, zonder valse regels |
| Draaien (MIT-26) | De ontwikkelserver van Flask, als root | Gunicorn, als de gebruiker `app`, zonder schrijfrecht op de code |
| Databaserol (MIT-27) | De app logde in als superuser: tabellen weggooien en rollen maken lukte | `notities_app` mag alleen lezen en schrijven in de eigen tabellen; het wachtwoord van de eigenaar zit niet meer in de app |
| Terug na uitloggen (MIT-28) | De notities stonden weer in beeld | De inlogpagina; geen pagina in de cache |
| Sessieduur (MIT-29) | Een cookie van 30 dagen oud werkte nog | Hooguit 8 uur |
| Registreren en notities (MIT-30) | 15 registraties vanaf één adres en 30 notities gingen allemaal door; `/login` werd trager voor anderen | 10 per uur per adres, dan 429; 25 notities per account |
| `.env` (MIT-32) | Op Linux leesbaar voor elke gebruiker (0644) | Alleen de eigenaar (0600) |
| Updates (MIT-33) | Vastgezet, en niets waarschuwt bij een nieuwe versie | Dependabot opent elke week een pull request |

## Hoe het werkt

- **CSRF-token (MIT-20).**
  - Elke sessie krijgt een willekeurig token van 32 bytes. Elk van de 14 formulieren stuurt het mee in een verborgen veld.
  - Een POST zonder het juiste token krijgt 400. De vergelijking gebeurt in constante tijd, zoals OWASP aanraadt.
  - De controle draait vóór het laden van de gebruiker, zodat een verlopen sessie gewoon naar de inlogpagina gaat.
  - Daarnaast heeft de cookie `SameSite=Lax`.
- **Headers (MIT-21).**
  - De CSP: `default-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'`.
  - Daarbij `X-Frame-Options: DENY`, `nosniff` en `Referrer-Policy: same-origin`.
  - HSTS alleen als de app op HTTPS draait.
- **Invoer (MIT-22).**
  - De gebruikersnaam gaat door een allowlist met `fullmatch`: `[A-Za-z0-9_]{3,20}`. Bij registreren volgt een melding. Bij inloggen en wachtwoord vergeten telt een andere naam als onbekend, met hetzelfde antwoord.
  - De browser controleert hetzelfde met `pattern`, maar dat is alleen gemak: de server beslist.
  - `MAX_CONTENT_LENGTH` is 16 KiB.
  - Alleen een POST voert een formulieractie uit.
- **Configuratie (MIT-23).** De app start niet als een van deze waarden niet klopt:

  | Instelling | Wat er moet |
  |---|---|
  | `TRUSTED_PROXIES` | 0 of 1 |
  | `HTTPS_ONLY` | 0 of 1; zonder waarde 1 |
  | `FLASK_SECRET_KEY` | Minstens 32 tekens |
  | `DATA_ENCRYPTION_KEY` | 256 bits |
  | `THROTTLE_IP_MODE` | Een bekende stand |
- **Standaard dicht (MIT-24).** Eén hook (`require_login`) vraagt voor elke route een login met tweestapsverificatie. Alleen `PUBLIC_ENDPOINTS` mag zonder.
- **Veilig falen (MIT-25).**
  - HTTP-fouten krijgen de eigen foutpagina, met behoud van status en headers. Die pagina toont een grote robot die het heeft begeven, met de statuscode op zijn borst; een inline SVG zonder `style`-attributen, met de opmaak en animatie in `style.css`, zodat de CSP streng blijft.
  - Een onverwachte fout geeft "Something went wrong". De fout zelf gaat met traceback naar stderr: lokaal `docker compose logs`, op Azure de log van Container Apps.
  - Het pad gaat als repr de log in, dus een regeleinde in de URL wordt `\n`.
- **Gewone gebruiker (MIT-26).** De image maakt de systeemgebruiker `app` zonder shell en draait daaronder, met Gunicorn en twee workers. De code is van root, dus de app kan hem lezen maar niet aanpassen.
- **Databaserol (MIT-27).**
  - `db/schema.sql` maakt de rol `notities_app`, geen superuser en nergens eigenaar van. Hij krijgt `SELECT`, `INSERT`, `UPDATE` en `DELETE` op de drie tabellen en `USAGE` op de twee sequences: precies wat de app doet.
  - Lokaal zet `db/app-password.sh` het wachtwoord bij de eerste start van een leeg volume. Het komt uit `APP_DB_PASSWORD` in `.env`, dat `scripts/deployment.py` aanmaakt. De app krijgt alleen dat wachtwoord.
  - Op Azure staat het wachtwoord van de eigenaar in een eigen Key Vault. Alleen de schema-job leest die, met een eigen identiteit. De job maakt het schema in een lege database en zet bij elke start het wachtwoord van de app-rol, en Terraform start hem zelf, ook na een nieuw wachtwoord (`secret_version`). Op Azure gemeten: de app heeft geen rol op de vault van de eigenaar (T-86).
- **Geen cache (MIT-28).** Elk antwoord behalve CSS en scripts krijgt `Cache-Control: no-store`, zoals de OWASP Session Management Cheat Sheet aanraadt. Na uitloggen vraagt Terug de pagina opnieuw op, en dan stuurt de app naar de inlogpagina.
- **Sessieduur (MIT-29).** `PERMANENT_SESSION_LIFETIME` is 8 uur. Flask controleert bij elk verzoek hoe oud de handtekening van de cookie is, ook bij een cookie die alleen voor de browsersessie geldt; dat staat in de broncode van Flask 3.1.3. Zonder deze regel was het 31 dagen.
- **Limieten (MIT-30).** Elke registratie telt per adres, met de tellers van de poginglimieten: 10 per uur, in de hackstand 60. De teller staat vlak voor het hashen, dus alleen een registratie die echt rekent, telt. Een notitie wordt geteld en toegevoegd in één statement, tot 25 per account.
- **`.env` (MIT-32).** `deployment.py` zet het bestand op 0600 voordat het iets schrijft, en zet een bestaand bestand ook recht.
- **Dependabot (MIT-33).** `.github/dependabot.yml` controleert elke week pip, de Dockerfile, `compose.yaml`, Terraform en de GitHub Actions. In de BoK hoort het bij CI/CD (Week 8), maar er is geen pipeline voor nodig.
- **Eén UPDATE (MIT-09).** Een nieuw wachtwoord of een 2FA-wijziging hoogt in hetzelfde statement de sessieversie op. Valt de verbinding weg, dan is het allebei of niets.

## Waarom het veilig is

| Wat | Hoe | Gemeten |
|---|---|---|
| Een andere site kan niets laten doen | Zonder het token van de sessie 400, ook met de cookie erbij | T-16, T-73 |
| Geen frame op een andere site | `frame-ancestors 'none'` en `X-Frame-Options: DENY` | T-74 |
| Een script dat erdoor glipt, draait niet | Een CSP zonder inline script; geen enkele overtreding op de echte pagina's | T-18, T-75 |
| Te grote invoer kost niets | 413 voordat het verzoek is ingelezen | T-21, T-76 |
| Alleen geldige gebruikersnamen | Allowlist met `fullmatch`, op de server | T-77 |
| Alleen een POST telt | HEAD en GET tonen alleen de pagina | T-78 |
| Een verkeerde instelling valt op | De app start niet, met een duidelijke melding | T-79 |
| Geen route per ongeluk open | De test haalt alle routes uit de app en opent ze anoniem | T-80 |
| Geen details naar buiten, geen valse logregels | Eigen foutpagina's; het pad als repr | T-81 |
| Overname is geen root | `app`, Gunicorn, geen schrijfrecht op `/app` | T-82 |
| Overname is geen databasebeheer | `notities_app`: geen tabellen maken of weggooien, geen rollen, geen `COPY` naar een programma | T-19, T-83 |
| De app kent het wachtwoord van de eigenaar niet | Niet in de omgeving van de app; op Azure in een vault die alleen de schema-job leest | T-84, T-86 |
| De schema-job mag opnieuw | Het schema alleen in een lege database; het wachtwoord als tekst, niet als SQL | T-85 |
| Geen notities na uitloggen | `no-store` op elke pagina; getest met de Terug-knop in Edge | T-89 |
| Een oude cookie werkt niet | Ondertekend alsof het 9 uur of 30 dagen geleden was: naar de inlogpagina | T-90 |
| Massaal aanmaken stopt | De 11e registratie en de 26e notitie worden geweigerd | T-91, T-92 |
| Sleutels niet voor anderen | `.env` 0600, ook een bestaand bestand | T-95 |

## Secrets management

Staat in Week 6, onder "Key management en secrets":
- drie aparte sleutels, zelf gemaakt met de module `secrets`, nooit in git;
- de gegevenssleutel buiten de database;
- op Azure in Key Vault, met de geheimen buiten de Terraform-state.

Week 7 voegt de controle bij het starten toe. Een te korte sessiesleutel of een gegevenssleutel van de verkeerde lengte laat de app niet starten (MIT-23). En de app krijgt een eigen databasewachtwoord (A-10), zodat dat van de eigenaar (A-06) uit de app kan (MIT-27).

## Database security

Zonder overkill: wat de app nodig heeft, en verder niets.

| Laag | Wat | Waar |
|---|---|---|
| Queries | Altijd met parameters, nooit tekst erin geplakt | MIT-02 |
| Rechten | Een eigen rol met alleen lezen en schrijven in de eigen tabellen | MIT-27 |
| Wachtwoorden | Het wachtwoord van de eigenaar niet in de app; op Azure in een eigen vault | MIT-27 |
| Gevoelige kolommen | TOTP-geheim en notities versleuteld, wachtwoorden als Argon2id-hash | MIT-17 tot MIT-19 (Week 6) |
| Netwerk | Lokaal alleen op het Docker-netwerk, zonder poort naar buiten; op Azure alleen privé, met TLS 1.3 en `verify-full` | B-02, `terraform/database.tf` |

Bewust niet: rechten per rij (row-level security), een audit-log in de database en een eigen schijfsleutel. De app filtert al zelf op `user_id` (MIT-15); wat er gelogd wordt, beslist de logging-stap.

## Secure coding standard: OWASP Top 10 Proactive Controls (2024)

| Control | In deze app |
|---|---|
| C1 Implement Access Control | Eigenaarscontrole op notities (MIT-15), herauthenticatie (MIT-16), standaard dicht (MIT-24), een databaserol met minimale rechten (MIT-27) |
| C2 Use Cryptography to Protect Data | AES-256-GCM voor het TOTP-geheim en de notities, Argon2id voor wachtwoorden (Week 6) |
| C3 Validate all Input & Handle Exceptions | Parameterized queries (MIT-02), lengtegrenzen (MIT-04), invoer en configuratie (MIT-22, MIT-23), veilig falen (MIT-25) |
| C4 Address Security from the Start | Elke feature begint bij de misuse cases in de BoK; de uitgewerkte dreigingsanalyse en het ontwerp (Week 3 en 5) volgen aan het eind |
| C5 Secure By Default Configurations | `HTTPS_ONLY` standaard aan, de hackstand standaard uit, `TRUSTED_PROXIES` standaard 0, geen root (MIT-23, MIT-26) |
| C6 Keep your Components Secure | Alles vastgezet, ook wat er meekomt en de base-images op digest (MIT-03); in de pipeline maakt Trivy van elke image een SBoM en scant die, ook bij elke pull request (MIT-35, MIT-36, MIT-39, Week 8) |
| C7 Secure Digital Identities | Verplichte 2FA, poginglimieten, sessieversie, Argon2id (Week 5 en 6) |
| C8 Leverage Browser Security Features | CSP, `frame-ancestors`, `nosniff`, `Referrer-Policy`, `HttpOnly`, `SameSite`, `Secure` (MIT-21, MIT-23) |
| C9 Implement Security Logging and Monitoring | Elke security-gebeurtenis een JSON-regel (MIT-31, Week 6 Logging), onverwachte fouten met traceback (MIT-25) |
| C10 Stop Server Side Request Forgery | Niet van toepassing: de app doet geen verzoeken naar adressen die een gebruiker kiest |

## Wat het niet oplost

- **De melding "al in gebruik" verraadt namen (MC-09).** De limiet op registreren maakt een lijst opbouwen wel trager: 10 namen per uur per adres.
- **Wie veel adressen heeft, omzeilt de limiet op registreren.** Per adres 10 accounts per uur, elk met 25 notities.
- **Een sessie waaruit niet is uitgelogd, werkt nog tot 8 uur.** Op een gedeelde computer is uitloggen dus nog steeds nodig.
- **Dependabot stelt alleen voor.** Iemand moet de pull request bekijken en samenvoegen. Of hij ook de digests van de images bijwerkt, laat de eerste pull request zien (T-97).
- **De app-rol mag nog alles wat de app mag (MC-08).** Na een overname kan een aanvaller alle rijen lezen, wijzigen en wissen, bijvoorbeeld tweestapsverificatie uitzetten. Notities en geheimen blijven wel versleuteld.
- **Lokaal staan beide databasewachtwoorden in `.env`.** Wie de ontwikkelmachine heeft, heeft ze allebei. De scheiding helpt tegen een overname van de app, niet tegen een overname van de machine.
- **Een bestaand volume krijgt de rol niet.** `db/schema.sql` draait alleen in een leeg volume. Wie de stack al had: `docker compose down -v` (wist de lokale data) en daarna `python scripts/deployment.py`.
- **De CSP staat scripts uit eigen bestanden toe.** Wie daar iets in krijgt, heeft de server al.
- **`TRUSTED_PROXIES` controleert alleen onzin.** Het juiste getal is kennis over de uitrol: Terraform zet 1 voor Container Apps.
- **Het bestandssysteem van de container is niet alleen-lezen.** De code is wel beschermd, maar bijvoorbeeld `/tmp` niet.

## Keuzes

- **Een eigen CSRF-module van 20 regels, geen Flask-WTF.** Hetzelfde patroon als OWASP beschrijft, zonder extra pakketten (MC-11). Flask-WTF zou ook WTForms meebrengen, en die gebruiken we niet.
- **Een token per sessie, niet per verzoek.** OWASP noemt beide; per verzoek geeft fouten met de terugknop.
- **Een strikte CSP zonder `unsafe-inline`.** Dat kon, omdat de templates al geen inline script of style hadden.
- **`X-Frame-Options` naast `frame-ancestors`.** OWASP noemt `X-Frame-Options` verouderd, maar raadt aan om waar mogelijk meer dan één maatregel te nemen, voor oudere browsers.
- **`TRUSTED_PROXIES` alleen 0 of 1, niet 0 tot en met 2.** Met 2 kiest de aanvaller in deze opzet zelf zijn adres; dat liet de voor-meting zien. Komt er ooit een tweede proxy bij (zoals Front Door), dan gaat het bewust omhoog.
- **`HTTPS_ONLY` standaard aan.** Vergeten moet de veilige kant op vallen: dan werkt inloggen over HTTP niet, in plaats van dat de cookie onversleuteld gaat.
- **De HEAD-fout is gevonden bij het maken van de voor-screenshots.** `curl -I` gaf 400 op de inlogpagina. De oorzaak: de routes keken of het verzoek GET was, en deden anders wat bij POST hoort. Nu is het andersom, zoals OWASP aanraadt: alleen een POST verandert iets.
- **16 KiB.** Het grootste echte formulier is een notitie van 250 tekens. Ruim genoeg, en een verzoek van 5 MB kost niets meer.
- **Gunicorn met twee workers, zonder access-log.** Twee workers passen bij 0,25 vCPU op Container Apps. De security-events staan in de log (MIT-31); gewone verzoeken niet, ook de healthchecks niet.
- **8 uur na het inloggen, niet 8 uur na het laatste verzoek.** Een grens die met elk verzoek opschuift, verdwijnt bij een tabblad dat openblijft. BOK-SECENGINEER gebruikte ook 8 uur; OWASP noemt 4 tot 8 uur als voorbeeld van een absolute timeout.
- **De limiet op notities zonder slot.** Gelijktijdige verzoeken kunnen er samen een paar overheen, hooguit één per worker. Een slot zou elke notitie trager maken, voor een grens die alleen de groei afremt.
- **De hackstand voor registreren op 60 per uur.** BOK-SECENGINEER had 30; een klas van zo'n 30 met een tweede account komt daar snel boven.
- **Een eigen vault voor het wachtwoord van de eigenaar, geen rechten per geheim.** Microsoft raadt een vault per applicatie aan en geen rollen op losse geheimen; een van de twee uitzonderingen die Microsoft noemt, is een geheim dat twee applicaties delen. Die gebruiken we één keer: de schema-job leest ook het wachtwoord van de app-rol.
- **De rol in `schema.sql`, het wachtwoord erbuiten.** `schema.sql` staat in git; het wachtwoord komt uit `.env` of Key Vault. Lokaal zet psql het met `:'password'` als letterlijke tekst, op Azure de job met `sql.Literal`.
- **Geen bonusonderwerpen.** Compileropties zijn voor Python niet van toepassing. Het ondertekenen van de container-image (bijvoorbeeld met cosign) past bij de pipeline in Week 8.

## Screenshots

Voor het verslag, lokaal in `screenshots/Week 7 Application Security/` (niet in de repo).

| Onderdeel | Voor | Na | Code |
|---|---|---|---|
| CSRF | `week7_voor_csrf_1_andere_site`, `_2_notitie_aangemaakt` | `week7_na_csrf_1_geweigerd`, `_2_geen_notitie` | `week7_code_1_csrf` |
| Clickjacking en headers | `week7_voor_clickjacking_1_in_frame`, `week7_voor_headers_1_geen_headers` | `week7_na_clickjacking_1_frame_geweigerd`, `week7_na_headers_1_csp_en_meer` | `week7_code_2_headers` |
| Gebruikersnaam | `week7_voor_naam_1_html_als_naam` | `week7_na_naam_1_geweigerd` | `week7_code_3_invoer` |
| Grootte van een verzoek | `week7_voor_groot_1_5mb_ingelezen` | `week7_na_groot_1_413` | `week7_code_3_invoer` |
| HEAD telt als poging | `week7_voor_head_1_telt_als_poging` | `week7_na_head_1_telt_niet` | `week7_code_3_invoer` |
| `TRUSTED_PROXIES` | `week7_voor_proxies_1_niet_gecontroleerd` | `week7_na_proxies_1_alleen_0_of_1` | `week7_code_4_configuratie` |
| Standaard dicht | geen (er stond geen route open) | bewezen met T-80 | `week7_code_5_standaard_dicht` |
| Veilig falen | geen | `week7_na_fout_1_korte_melding`, `_2_in_de_log` | `week7_code_6_veilig_falen` |
| Root en ontwikkelserver | `week7_voor_root_1_ontwikkelserver_als_root` | `week7_na_root_1_gunicorn_als_app` | `week7_code_6_veilig_falen` |
| Databaserol | `week7_voor_rol_1_superuser` | `week7_na_rol_1_eigen_rol` | `week7_code_7_databaserol` |
| Terug na uitloggen | `week7_voor_terug_1_notities_na_uitloggen` | `week7_na_terug_1_inlogpagina` | `week7_code_8_cache_en_sessie` |
| Sessieduur | `week7_voor_sessie_1_31_dagen` | `week7_na_sessie_1_8_uur` | `week7_code_8_cache_en_sessie` |
| Registreren en notities | `week7_voor_limieten_1_geen_limiet` | `week7_na_limieten_1_10_per_uur_25_notities` | `week7_code_9_limieten` |
| `.env` | `week7_voor_env_1_leesbaar_voor_iedereen` | `week7_na_env_1_alleen_eigenaar` | `week7_code_8_cache_en_sessie` |

## Bronnen

Opgehaald en gecontroleerd op 17-10-2026.

- OWASP Top 10 Proactive Controls 2024: https://top10proactive.owasp.org/the-top-10/
- OWASP Cross-Site Request Forgery Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- OWASP Input Validation Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
- OWASP Clickjacking Defense Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html
- OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- Docker, Building best practices (`USER`): https://docs.docker.com/build/building/best-practices/
- Werkzeug 3.1.9, `ProxyFix` (broncode): https://github.com/pallets/werkzeug/blob/3.1.9/src/werkzeug/middleware/proxy_fix.py
- PostgreSQL 18, `COPY` (alleen superuser of `pg_*_server_*` voor een bestand of programma): https://www.postgresql.org/docs/18/sql-copy.html
- PostgreSQL 18, Schemas (geen `CREATE` voor `PUBLIC` op `public` sinds 15): https://www.postgresql.org/docs/18/ddl-schemas.html
- Microsoft, Key Vault met Azure RBAC (een vault per applicatie, geen rollen per geheim): https://learn.microsoft.com/en-us/azure/key-vault/general/rbac-guide
- OWASP Session Management Cheat Sheet (`no-store`, een absolute timeout, 4 tot 8 uur als voorbeeld): https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html
- GitHub, door Dependabot ondersteunde ecosystemen (pip, docker, docker-compose, terraform): https://docs.github.com/en/code-security/dependabot/ecosystems-supported-by-dependabot/supported-ecosystems-and-repositories
