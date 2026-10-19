# Standards

Vier standaarden, elk voor een eigen laag:

- **De app: OWASP Top 10 Proactive Controls (2024).** De hoofdstandaard. Alle tien zijn afgedekt, of bewust niet van
  toepassing (C10). De tabel per control staat in Week 7.
- **Controleren: OWASP ASVS 5.0,** per hoofdstuk. De Proactive Controls zeggen wat je doet; ASVS zegt wat je moet
  kunnen nagaan. Hieronder: welk hoofdstuk van toepassing is, met welke maatregelen, en wat open staat.
- **De cloud: CSA Cloud Controls Matrix (CCM),** als tweede laag. Per domein: wat Azure doet, wat wij doen, en wat
  open staat.
- **EN 40000, kort.** De normen onder de CRA; nog in ontwikkeling. Wat de app al doet voor het afhandelen van
  kwetsbaarheden, en wat ontbreekt.

De details staan in de entries (de MIT's en MC's hieronder), de architectuur (A-, C-, F- en AZ-nummers) en de tests.

## OWASP Top 10 Proactive Controls (2024)

Geschreven voor ontwikkelaars: per control een werkwijze, niet een lijst eisen. Dat past bij een kleine app die door
één persoon gebouwd wordt. De volledige mapping op de MIT's staat in `Week 7 Application Security.md`; samengevat:

| Control | Afgedekt | Wat open staat |
|---|---|---|
| C1 Access Control | MIT-15, MIT-16, MIT-24, MIT-27 | Geen rechten per rij in de database (MC-08) |
| C2 Cryptography | MIT-17, MIT-18, MIT-19, MIT-40 | De gegevenssleutel zit in de draaiende app (MC-22) |
| C3 Input en exceptions | MIT-02, MIT-04, MIT-22, MIT-23, MIT-25 | |
| C4 Security from the Start | De misuse cases bij elke feature, de risicomatrix en de diagrammen in `Threat Analysis/` | |
| C5 Secure by Default | MIT-23, MIT-26 | |
| C6 Components | MIT-03, MIT-33, MIT-35, MIT-36, MIT-39 | De enige hoge in de risicomatrix: een lek na de build (MC-11) |
| C7 Digital Identities | MIT-05, MIT-06, MIT-09, MIT-10, MIT-12, MIT-19 | TOTP is niet bestand tegen phishing (MC-16) |
| C8 Browser Security Features | MIT-21, MIT-23 | |
| C9 Logging en Monitoring | MIT-31, MIT-37 | Alleen een blokkade geeft een mail (MC-28) |
| C10 Server Side Request Forgery | Niet van toepassing: de app haalt geen adressen op die een gebruiker kiest | |

## OWASP ASVS 5.0, per hoofdstuk

Gemapt per hoofdstuk, niet per eis: de app is niet eis voor eis geverifieerd tegen een niveau. Wat er gebouwd is,
is wel gemeten; dat zijn de tests in `Threat Analysis/tests.md`.

| Hoofdstuk | Van toepassing | In deze app | Open |
|---|---|---|---|
| V1 Encoding and Sanitization | Ja | Jinja escapet (MIT-01), queries met parameters (MIT-02), het pad als repr in de log (MIT-25) | |
| V2 Validation and Business Logic | Ja | Een allowlist voor de gebruikersnaam en lengtegrenzen (MIT-22, MIT-04), limieten op registreren en notities (MIT-30) | |
| V3 Web Frontend Security | Ja | CSP, `frame-ancestors`, `nosniff` en `Referrer-Policy` (MIT-21), cookievlaggen (MIT-23), HSTS op Azure (MIT-40) | |
| V4 API and Web Service | Nee | Geen API | |
| V5 File Handling | Nee | Geen uploads | |
| V6 Authentication | Ja | Argon2id (MIT-19), 12 tot 64 tekens (MIT-13), verplichte TOTP (MIT-05, MIT-12), limieten (MIT-06, MIT-10), herstelcode en wachtwoord vergeten (MIT-11, MIT-14) | Geen blocklist van veelgebruikte wachtwoorden (MC-03); TOTP is niet phishingbestendig (MC-16) |
| V7 Session Management | Ja | Sessieversie (MIT-09), hooguit 8 uur (MIT-29), opnieuw bewijzen bij wachtwoord, account en tweede factor (MIT-16) | Een gekopieerde cookie werkt tot hij verloopt (MC-04) |
| V8 Authorization | Ja | Eigenaarscontrole (MIT-15), standaard dicht (MIT-24) | |
| V9 Self-contained Tokens | Deels | De sessiecookie van Flask is ondertekend en bevat de sessieversie, die de server bij elk verzoek controleert (MIT-09); geen JWT | |
| V10 OAuth and OIDC | Nee | Geen OAuth of OIDC | |
| V11 Cryptography | Ja | AES-256-GCM met de gebruiker als associated data (MIT-17, MIT-18), Argon2id (MIT-19), de sleutels in Key Vault (AZ-10) | Nog geen rotatie: `v2:` is voorbereid, niet gebouwd |
| V12 Secure Communication | Ja | TLS 1.2 en 1.3 op Azure, getoetst aan het NCSC (MIT-40, T-113); naar de database TLS 1.3 met `verify-full` (F-03) | Lokaal geen TLS; het certificaat van Azure is RSA-2048 |
| V13 Configuration | Ja | Configuratie gecontroleerd bij het starten (MIT-23), geen debugmodus (MIT-25), geheimen uit Key Vault, vaste versies (MIT-03) | |
| V14 Data Protection | Ja | Geen pagina in de cache (MIT-28), notities versleuteld (MIT-18), geen wachtwoord of code in de log (MIT-31) | Hoeveel notities iemand heeft en wanneer, blijft leesbaar (MC-23) |
| V15 Secure Coding and Architecture | Ja | Vaste versies, Dependabot, SBoM en scan bij elke pull request (MIT-03, MIT-33, MIT-35, MIT-36, MIT-39), Gunicorn als gewone gebruiker (MIT-26) | Een lek dat na de build bekend wordt (MC-11) |
| V16 Security Logging and Error Handling | Ja | Elke security-gebeurtenis als JSON-regel (MIT-31), veilig falen (MIT-25), een mail bij een blokkade (MIT-37) | Alleen een blokkade geeft een mail (MC-28) |
| V17 WebRTC | Nee | Geen WebRTC | |

## CSA Cloud Controls Matrix, de cloudlaag

De CCM heeft 17 domeinen; versie 4.1 (januari 2026) heeft 207 controls. Het bruikbaarste voor deze app is het idee
van gedeelde verantwoordelijkheid (het Shared Security Responsibility Model, in het domein STA): per control wat de
cloudleverancier doet, en wat de klant zelf moet doen. De tabel hieronder is dat model voor deze app. Waar een
controlnummer staat, komt het uit versie 4.0; 4.1 voegde 11 controls toe in DCS, LOG, SEF, STA en TVM, dus daar kan
de nummering afwijken.

| Domein | Azure doet | Wij doen | Open |
|---|---|---|---|
| AIS, Application & Interface Security | | Secure coding (Week 7); bij elke pull request een scan van de afhankelijkheden (MIT-39) | Nog geen SAST of DAST (AIS-05) |
| CCC, Change Control & Configuration Management | | Alles via een pull request met een verplichte check, zonder uitzonderingen (MIT-39, T-112; CCC-04); Terraform wacht op `yes` | Niemand anders kijkt mee: er is één beheerder |
| CEK, Cryptography, Encryption & Key Management | De database op schijf versleuteld, met een sleutel van Azure; Key Vault | Kolomversleuteling en Argon2id in de app (CEK-03); de state met een eigen RSA-4096-sleutel (MIT-38, CEK-08) | Geen rotatie van de gegevenssleutel (CEK-12) |
| DSP, Data Security & Privacy | | Wat er is en waar het heen gaat: de assets en datastromen in `Architecture/` (DSP-03, DSP-05); de log 30 dagen; alles in France Central, in de EU (DSP-19) | Een DPIA hoort bij Laws & compliance, overgeslagen |
| IAM, Identity & Access Management | Entra ID, managed identities en rollen | Per identiteit alleen de rol die nodig is (AZ-10 tot AZ-15; IAM-05); verplichte 2FA in de app, en een tweede stap voor de beheerder bij Azure (IAM-14) | De beheerder is Owner op de subscription (MC-31) |
| IVS, Infrastructure & Virtualization Security | Het netwerk, de hosts en de ingress | De database zonder openbaar adres, alleen bereikbaar uit het eigen netwerk (F-03; IVS-03, IVS-06) | |
| LOG, Logging & Monitoring | Log Analytics bewaart de log; de app kan er niet bij | De security-events (MIT-31); de app heeft geen rol op de workspace (AZ-13); een alert bij een blokkade (MIT-37) | Andere aanvallen geven geen alert (MC-28) |
| TVM, Threat & Vulnerability Management | Updates van het platform | Dependabot en de scan op bekende lekken (MIT-33, MIT-35, MIT-39); de pentest is de hacking week | De draaiende image wordt niet opnieuw gescand (MC-11) |
| BCR, Business Continuity & Operational Resilience | Een backup van de database, 7 dagen (`backup_retention_days`); de vaults 90 dagen terug te halen | `deployment.py` zet alles opnieuw neer (Week 8) | Geen backup in een tweede regio; nooit een terugzetting getest |

Niet van toepassing op deze app, maar bij Azure of bij een organisatie: DCS (de datacenters), HRS (personeel), GRC,
A&A (audits), IPY (overstappen naar een andere cloud) en UEM (laptops en telefoons). SEF (incidenten) is klein: er is
een mail bij een blokkade, maar geen incidentplan.

## EN 40000, kort

De EN 40000-reeks zijn de geharmoniseerde normen onder de CRA, gemaakt in CEN/CLC JTC 13 WG9. EN 40000-1-2 gaat over
de principes, het risicobeheer en de levenscyclus van een product (DKE); prEN 40000-1-3, het afhandelen van
kwetsbaarheden, wordt als eerste verwacht. Op 11-09-2026 was er nog geen enkele CRA-norm in het Publicatieblad
aangewezen (cyberresilienceact.eu). De tekst van de ontwerpen heb ik niet; daarom hier de eisen die deel
1-3 uitwerkt: bijlage I, deel II van de CRA. Of de CRA voor deze app geldt, hoort bij Laws & compliance, en dat is
overgeslagen.

| Eis uit bijlage I, deel II | In deze app |
|---|---|
| 1. Componenten vastleggen, met een SBoM in een gangbaar, machineleesbaar formaat, minstens de directe afhankelijkheden | Een CycloneDX-SBoM van elke image, met alle onderdelen (MIT-36, T-106) |
| 2. Kwetsbaarheden zonder vertraging aanpakken, ook met beveiligingsupdates | Dependabot elke week, en de scan bij elke pull request en vóór het publiceren (MIT-33, MIT-35, MIT-39) |
| 4. Opgeloste kwetsbaarheden openbaar maken | Nog niet |
| 5. Een beleid voor gecoördineerde melding van kwetsbaarheden | Nog niet: een `SECURITY.md` staat op de lijst vóór de hacking week |

## Wat het niet oplost

- **Een mapping is geen audit.** Dat een maatregel bij een control staat, zegt niet dat de control helemaal is
  afgedekt; ASVS is per hoofdstuk gemapt, niet eis voor eis geverifieerd.
- **Het deel van Azure is niet getoetst.** Wat er in de kolom "Azure doet" staat, komt uit de configuratie en de
  documentatie, niet uit een eigen meting; alleen de TLS is gemeten (T-113).
- **EN 40000 bestaat nog niet als norm.** De eisen uit de CRA zijn wel definitief; de normen die ze uitwerken nog niet.

## Keuzes

- **Proactive Controls als hoofdstandaard.** Kort, voor ontwikkelaars, en het past bij hoe de app gebouwd is: per
  feature een maatregel. Eerder in de dreigingsanalyse van 7-10-2026 ook al gekozen.
- **ASVS per hoofdstuk, niet per eis.** Eis voor eis is voor een app van deze omvang veel werk dat weinig toevoegt;
  per hoofdstuk laat het zien wat van toepassing is en waar de gaten zitten.
- **Van de CCM alleen de domeinen die bij de app horen,** met het model van gedeelde verantwoordelijkheid als kern.
  De rest gaat over datacenters, personeel of een organisatie.
- **EN 40000 kort.** Nog niet aangewezen, en het hoort bij een wet die buiten deze BoK valt.

## Bronnen

Opgehaald en gecontroleerd op 19-10-2026.

- OWASP Top 10 Proactive Controls 2024: https://top10proactive.owasp.org/the-top-10/
- OWASP ASVS 5.0, de hoofdstukken V1 tot V17: https://github.com/OWASP/ASVS/tree/master/5.0/en
- CSA, CCM v4.1 (17 domeinen, 207 controls, 11 nieuwe in DCS, LOG, SEF, STA en TVM; verschenen in januari 2026): https://cloudsecurityalliance.org/articles/the-csa-cloud-controls-matrix-v4-1-strengthening-the-future-of-cloud-security
- Open Security Architecture, de controls van CCM v4.0 met nummer en titel (een eigen samenvatting, niet regel voor regel gecontroleerd tegen CSA): https://opensecurityarchitecture.org/frameworks/csa-ccm-v4
- DKE, normprojecten voor de CRA (EN 40000-1-2): https://www.dke.de/resource/blob/2435170/a4c8225091ac18023516487e3e55cb23/normungsprojekte-zum-cra-data.pdf
- cyberresilienceact.eu (i46 s.r.o., onafhankelijk, geen juridisch advies), 30-07-2026, bijgewerkt 11-09-2026: prEN 40000-1-3 als eerste verwacht, nog geen norm aangewezen: https://www.cyberresilienceact.eu/news/cra-standardisation-deadlines-pushed-back-two-months.html
- Verordening (EU) 2024/2847 (CRA), bijlage I, deel II. EUR-Lex was niet op te halen; de tekst van punt 1, 2, 4 en 5 komt via Sonatype en het Center for Cybersecurity Policy: https://www.sonatype.com/eu-cyber-resilience-act-guide en https://centerforcybersecuritypolicy.org/insights-and-research/vulnerability-management-under-the-cyber-resilience-act
