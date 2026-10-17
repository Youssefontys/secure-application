# Week 7: Application Security

De app controleert nu alles wat binnenkomt, en valt veilig om als er iets misgaat:
- **Formulieren:** elk formulier draagt een CSRF-token (MIT-20).
- **Headers:** elk antwoord heeft een strikte CSP en verbiedt frames (MIT-21).
- **Invoer:** gebruikersnamen, de grootte van een verzoek en de HTTP-methode worden gecontroleerd (MIT-22).
- **Configuratie:** de configuratie wordt bij het starten gecontroleerd, met veilige standaarden (MIT-23).
- **Routes:** elke route is standaard dicht (MIT-24).
- **Fouten:** een fout geeft een korte melding, met de details alleen in de log (MIT-25).
- **Draaien:** de app draait met Gunicorn als gewone gebruiker, niet meer als root (MIT-26).

Daarmee zijn MC-05 (CSRF) en MC-14 (root en de ontwikkelserver) dicht, de laatste twee voorwaarden voor de uitrol naar Azure.

De details staan in de entries (MC-05, MC-07, MC-10, MC-14, MC-18, MC-24 tot MC-26; MIT-20 tot MIT-26) en de tests (T-16, T-18, T-21, T-73 tot T-82). Dit bestand vat ze samen.

## De dreiging

- **Een andere site** laat de ingelogde gebruiker een formulier versturen (MC-05), of laadt de app onzichtbaar in een frame en laat hem klikken (MC-24).
- **Iedere bezoeker** stuurt vreemde of te grote invoer (MC-10), lokt een fout uit om details te zien of de log te vervalsen (MC-26), of vindt een route die per ongeluk open staat (MC-25).
- **Een verkeerde instelling** laat een aanvaller zelf zijn adres kiezen en zo de poginglimieten omzeilen (MC-18).
- **Wie de app overneemt,** was root in de container (MC-14).

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
  - HTTP-fouten krijgen de eigen foutpagina, met behoud van status en headers.
  - Een onverwachte fout geeft "Er ging iets mis". De fout zelf gaat met traceback naar stderr: lokaal `docker compose logs`, op Azure de log van Container Apps.
  - Het pad gaat als repr de log in, dus een regeleinde in de URL wordt `\n`.
- **Gewone gebruiker (MIT-26).** De image maakt de systeemgebruiker `app` zonder shell en draait daaronder, met Gunicorn en twee workers. De code is van root, dus de app kan hem lezen maar niet aanpassen.

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

## Secrets management

Staat in Week 6, onder "Key management en secrets":
- drie aparte sleutels, zelf gemaakt met de module `secrets`, nooit in git;
- de gegevenssleutel buiten de database;
- op Azure in Key Vault, met de geheimen buiten de Terraform-state.

Week 7 voegt de controle bij het starten toe. Een te korte sessiesleutel of een gegevenssleutel van de verkeerde lengte laat de app niet starten (MIT-23).

## Secure coding standard: OWASP Top 10 Proactive Controls (2024)

| Control | In deze app |
|---|---|
| C1 Implement Access Control | Eigenaarscontrole op notities (MIT-15), herauthenticatie (MIT-16), standaard dicht (MIT-24) |
| C2 Use Cryptography to Protect Data | AES-256-GCM voor het TOTP-geheim en de notities, Argon2id voor wachtwoorden (Week 6) |
| C3 Validate all Input & Handle Exceptions | Parameterized queries (MIT-02), lengtegrenzen (MIT-04), invoer en configuratie (MIT-22, MIT-23), veilig falen (MIT-25) |
| C4 Address Security from the Start | Elke feature begint bij de misuse cases in de BoK; de uitgewerkte dreigingsanalyse en het ontwerp (Week 3 en 5) volgen aan het eind |
| C5 Secure By Default Configurations | `HTTPS_ONLY` standaard aan, de hackstand standaard uit, `TRUSTED_PROXIES` standaard 0, geen root (MIT-23, MIT-26) |
| C6 Keep your Components Secure | Alles vastgezet, ook wat er meekomt (MIT-03); scannen komt in de pipeline (Week 8) |
| C7 Secure Digital Identities | Verplichte 2FA, poginglimieten, sessieversie, Argon2id (Week 5 en 6) |
| C8 Leverage Browser Security Features | CSP, `frame-ancestors`, `nosniff`, `Referrer-Policy`, `HttpOnly`, `SameSite`, `Secure` (MIT-21, MIT-23) |
| C9 Implement Security Logging and Monitoring | Alleen fouten in de log (MIT-25); security-events komen bij Logging en monitoring |
| C10 Stop Server Side Request Forgery | Niet van toepassing: de app doet geen verzoeken naar adressen die een gebruiker kiest |

## Wat het niet oplost

- **Security-events worden nog niet gelogd.** Mislukte logins en blokkades staan nergens. Dat komt bij Logging en monitoring, en werkt dan lokaal en op Azure hetzelfde, via stdout.
- **Registreren is onbeperkt (MC-10),** en de melding "al in gebruik" verraadt namen (MC-09).
- **De app logt nog in als eigenaar van de database (MC-08).** Een eigen rol volgt tussendoor, bij database security.
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
- **Gunicorn met twee workers, nog zonder access-log.** Twee workers passen bij 0,25 vCPU op Container Apps. Welke verzoeken worden gelogd, beslist de logging-stap.
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

## Bronnen

Opgehaald en gecontroleerd op 17-10-2026.

- OWASP Top 10 Proactive Controls 2024: https://top10proactive.owasp.org/the-top-10/
- OWASP Cross-Site Request Forgery Prevention Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
- OWASP Input Validation Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html
- OWASP Clickjacking Defense Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html
- OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- Docker, Building best practices (`USER`): https://docs.docker.com/build/building/best-practices/
- Werkzeug 3.1.9, `ProxyFix` (broncode): https://github.com/pallets/werkzeug/blob/3.1.9/src/werkzeug/middleware/proxy_fix.py
