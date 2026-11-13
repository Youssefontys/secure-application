# Week 9: extra's, de OWASP Cheat Sheets naast de app

Geen BoK-onderwerp, maar een controle: wat vragen de cheat sheets van OWASP die bij deze app passen, wat doet de app al, en wat
ontbreekt. Elke sheet is op 13-11-2026 gelezen (niet alleen de titel); de tabellen zijn mijn vergelijking met de repo, niet een
mapping van OWASP zelf. Status: **Gedaan**, **Deels**, **Open**, of **Bewust niet** (met de reden).

Aan het eind staan de voorstellen die eruit komen. Wat daarvan gebeurt, is nog niet besloten.

## 1. Infrastructure as Code Security

| Aanbeveling | In de app | Status |
|---|---|---|
| Geheimen buiten bestanden en scannen | Terraform maakt ze als ephemeral waarde en schrijft ze write-only naar Key Vault; de secret scan in de check (MIT-45, T-147) | Gedaan |
| Wijzigingen in versiebeheer; beperk wie wijzigt en wat de resources mogen | Alles via een pull request, een ruleset zonder bypass; de deploy-identiteit mag alleen de image vervangen (T-129) | Gedaan |
| Statische analyse | Trivy op `terraform/` bij elke wijziging (MIT-47) | Gedaan |
| Afhankelijkheden controleren | De providers staan vast op een versie met een lockfile (`.terraform.lock.hcl`); Dependabot stelt nieuwe versies voor (MIT-33) | Gedaan |
| Images scannen | Trivy op de SBoM, bij elke pull request en vóór het publiceren (MIT-35, MIT-39) | Gedaan |
| Checks automatiseren, met één overzicht | Drie workflows (image, IaC, DAST); geen gezamenlijk overzicht | Deels |
| Artefacten ondertekenen en de handtekening controleren | De image en de SBoM zijn niet ondertekend | Open |
| Inventaris en tags | Tags `app` en `managed_by` op de resources; geen aparte inventarislijst | Deels |
| Afbouwen: configuratie en data wissen | `deployment.py undo` haalt alles weg, ook lokaal; Key Vault houdt verwijderde geheimen 90 dagen (purge protection) | Gedaan |
| Dynamische analyse | ZAP baseline op de app (MIT-46); niet op de infrastructuur | Deels |
| Onveranderlijke infrastructuur | Elke nieuwe image is een nieuwe revisie, de oude blijft inactief (T-133) | Gedaan |
| Audit-logging bij het aanmaken van infrastructuur | De log van de app staat in Log Analytics; de activiteitenlog van Azure heeft geen alert | Deels |
| Bewaken en alarmeren | Een alert op blokkades (MIT-37); geen alert op wijzigingen aan rollen | Deels |
| Runtime threat detection | Niet aan | Bewust niet: kosten en omvang van de app |

## 2. Subdomain Takeover Prevention

Hoort bij het plan voor een eigen domein (Week 8, stap 13). De app heeft nu geen eigen domein, dus er is niets te nemen.

| Aanbeveling | Voor het eigen domein | Status |
|---|---|---|
| Het `asuid`-TXT-record bewaren, ook na het afbreken | Het record hoort bij de koppeling; niet weghalen | Gepland |
| DNS-records weghalen of verleggen **vóór** de resource wordt verwijderd | `deployment.py undo` verwijdert de container app; het moet eerst de `CNAME` laten weghalen | Gepland |
| Een DNS-inventaris: welk record bij welke resource hoort | Eén domein, twee records | Gepland |
| Regelmatig controleren op records die nergens meer naar wijzen | Bij elke nieuwe omgeving | Gepland |

## 3. Workload Identity Federation (de OIDC-uitrol)

| Aanbeveling | In de app | Status |
|---|---|---|
| Issuer, audience en subject vastzetten | Subject `repo:Youssefontys/secure-application:environment:azure` met vaste ID's, audience `api://AzureADTokenExchange` (T-127) | Gedaan |
| Vertrouwen beperken tot repo, branch en environment | De environment `azure` staat alleen `main` toe, met de beheerder als verplichte reviewer (T-129) | Gedaan |
| Aparte identiteiten voor productie en niet-productie | Eén omgeving, één identiteit | Bewust niet: er is geen tweede omgeving |
| Rechtenbeheer los van de deploy-rol | De rol mag alleen `ca-notes` lezen en wijzigen (T-129) | Gedaan |
| `id-token: write` alleen waar nodig | Alleen in de job `deploy`; de standaard is `permissions: {}` | Gedaan |
| Een korte levensduur van het token | Niet gecontroleerd | Open |
| Testen dat een onbevoegde context geen token krijgt | Een subject dat niet past is geweigerd (T-127); een andere branch of repo is niet apart getest | Deels |
| Auditlog en alert bij wijzigingen aan het vertrouwen | Geen alert | Open |

## 4. Docker Security

Naast de CIS Docker Benchmark in 5.2.7 van het verslag; dezelfde open punten, nu met de nummers van OWASP.

| Regel | In de app | Status |
|---|---|---|
| #1 De Docker-socket niet blootstellen | Niet gemount in `compose.yaml` | Gedaan |
| #2 Een gebruiker instellen | `USER app`, zonder shell en zonder schrijfrecht op de code (MIT-26) | Gedaan |
| #3 Capabilities beperken | Niet ingesteld | Open |
| #4 Geen extra rechten | setuid- en setgid-bits uit de image (MIT-42); de vlag `no-new-privileges` staat niet aan | Deels |
| #5 Verbindingen tussen containers beperken | De database heeft in Compose geen poort naar buiten; op Azure een privénetwerk | Gedaan |
| #5a Poorten alleen aan localhost binden | `127.0.0.1:5000:5000` | Gedaan |
| #6 Linux Security Modules aan laten | De standaardprofielen van Docker zijn niet aangepast | Gedaan |
| #7 Resources beperken | 0,25 vCPU en 0,5 GiB op Azure; niet in `compose.yaml` | Deels |
| #8 Root-bestandssysteem alleen-lezen | Niet ingesteld | Open |
| #9 Scannen in CI: linting, kwetsbaarheden en geheimen | Trivy op de image, Terraform en de bestanden; geen linter voor het Dockerfile | Deels |
| #12 Geen geheimen in de image of omgeving | Geen geheimen in de image (A-12); wel als omgevingsvariabele uit Key Vault, een bewuste afwijking (MC-22) | Deels |
| #13 Supply chain: provenance, SBoM, ondertekenen | SBoM en een vastgezette digest; geen handtekening of provenance | Deels |

## 5. Logging Vocabulary

De standaardnamen voor events, naast de 21 soorten van `events.py`.

| OWASP | Jouw soort | Status |
|---|---|---|
| `authn_login_success` | `login_ok` | Gedaan |
| `authn_login_fail` | `login_failed` | Gedaan |
| `authn_login_lock` | `lockout_started` | Gedaan |
| `authn_password_change` | `password_changed` | Gedaan |
| `authn_password_change_fail` | `reauth_failed` (het huidige wachtwoord klopt niet) | Gedaan |
| `session_logout` | `logout` | Gedaan |
| `session_expired`, `session_use_after_expire` | `session_rejected`, alleen voor een cookie met een oude sessieversie; een verlopen cookie is gewoon "niet ingelogd" | Deels |
| `malicious_csrf` | `csrf_refused` | Gedaan |
| `authz_fail`, `malicious_direct_reference` | Geen: andermans notitie geeft 404 zonder regel in de log (MC-02) | Open |
| `input_validation_fail` | Geen: een 400 op ongeldige invoer wordt niet gelogd | Open |
| `sensitive_read` en verwanten | Notities lezen of schrijven loggen past niet bij de privacy (A-11) | Bewust niet |
| `sys_startup`, `sys_crash` | Een fout staat in de log (MIT-25); opstarten niet | Deels |

## 6. Session Management

De sessie is een ondertekende Flask-cookie met `user_id` en `session_version`, geen ID in een sessiestore.

| Aanbeveling | In de app | Status |
|---|---|---|
| Nieuw ID na het inloggen | `start_session()` wist de sessie en zet een nieuwe | Gedaan |
| `Secure`, `HttpOnly`, `SameSite`, geen `Domain` | `Secure` standaard aan, `HttpOnly`, `SameSite=Lax`, geen `Domain` | Gedaan |
| De naam met het voorvoegsel `__Host-` | De naam is `session` | Open |
| Alleen via cookies, nooit in de URL | Ja | Gedaan |
| Een absolute time-out, op de server afgedwongen | 8 uur, gecontroleerd op de handtekening (MIT-29) | Gedaan |
| Een time-out bij inactiviteit (15 tot 30 minuten voor een app met laag risico) | Er is er geen | Open |
| Uitloggen ongeldig maken, ook aan de serverkant | `session_version` gaat omhoog bij uitloggen, wachtwoord of 2FA wijzigen (MIT-09) | Gedaan |
| `Cache-Control: no-store` | Op elke pagina (MIT-28) | Gedaan |
| `Clear-Site-Data` bij uitloggen | Niet | Open |
| De gegevens aan de serverkant, het ID betekenisloos | De cookie bevat het gebruikers-ID, leesbaar maar ondertekend | Bewust niet: een sessiestore is een extra onderdeel |
| Meerdere sessies tegelijk: kiezen, en laten inzien | Meerdere zijn toegestaan; de gebruiker kan ze niet zien | Open |
| Aanvallen op sessies herkennen en loggen | `session_rejected` bij een cookie met een oude sessieversie; een gewijzigde cookie heeft een ongeldige handtekening en is gewoon "niet ingelogd", zonder regel in de log | Deels |

## 7. Cookie Theft Mitigation

| Aanbeveling | In de app | Status |
|---|---|---|
| De blootstelling en de levensduur van de cookie beperken | Zie Session Management; de cookie is niet te lezen door script (`HttpOnly`) en 8 uur geldig | Gedaan |
| Diefstal herkennen met IP, User-Agent en taal bij het begin van de sessie | De IP-adressen staan in de log, maar de sessie wordt er niet mee vergeleken | Open |
| Bij een vermoeden de sessie beperken en opnieuw laten inloggen | Niet | Open |
| Apparaatgebonden sessiecredentials | Nog geen standaard in de browsers | Bewust niet |

## 8. Software Supply Chain Security

| Aanbeveling | In de app | Status |
|---|---|---|
| Peer review vóór het mergen | De ruleset eist een pull request en een groene check, maar nul goedkeuringen: er is één beheerder | Bewust niet: één beheerder |
| Beschermde branches | Geen bypass, geen force push, `main` kan niet worden verwijderd | Gedaan |
| Minimale rechten en MFA | Rechten per workflow; MFA op het GitHub-account (A-17, volgens de beheerder) | Gedaan |
| Geen geheimen in versiebeheer | Secret scanning van GitHub en de scan van Trivy (T-147) | Gedaan |
| Vertrouwde tools: actions vastzetten | Elke action op een commit (MIT-34), Dependabot houdt ze bij (MIT-33) | Gedaan |
| Een SBoM voor alle afhankelijkheden, automatisch | CycloneDX van de image bij elke build (MIT-36) | Gedaan |
| Bewaken tegen NVD, OSV en KEV | Trivy bij elke build; KEV en EPSS met de hand bij een nieuw lek (`vex/README.md`) | Deels |
| SAST | CodeQL (MIT-45) | Gedaan |
| Versies vastzetten met lockfiles | Alles vastgezet; hashes in `requirements.txt` nog niet (Week 8, stap 15) | Deels |
| Builds in tijdelijke, geïsoleerde omgevingen | Runners van GitHub, na elke run weg | Gedaan |
| Eindproduct scannen | De image wordt gescand (MIT-35) | Gedaan |
| Ondertekenen, en de handtekening controleren | Niet | Open |
| Provenance van het buildplatform, controleren met SLSA | Niet | Open |
| Wat draait bewaken op nieuwe lekken | Nog niet na de build (Week 8, stap 6) | Gepland |
| Een actuele inventaris van wat draait | De SBoM per build, 90 dagen bewaard | Gedaan |

## 9. CI CD Security

| Aanbeveling | In de app | Status |
|---|---|---|
| Geen geheimen in de CI-bestanden | Geen; het token van de run, en OIDC zonder sleutel | Gedaan |
| Minimale rechten per pipeline | `permissions: {}` en per job alleen wat nodig is (MIT-34) | Gedaan |
| De CI-configuratie in versiebeheer, en beoordeeld vóór het mergen | In versiebeheer; een pull request draait de workflow uit die pull request zelf (B-06, MC-30 stap 6) | Deels |
| SAST, DAST en IaC-scan in de pipeline | CodeQL, ZAP en Trivy op Terraform (MIT-45 tot MIT-47) | Gedaan |
| Handmatige goedkeuring vóór productie | De environment `azure` wacht op de beheerder (T-128) | Gedaan |
| Hashes van pakketten controleren | Nog niet | Deels |
| Geen auto-merge | Niet gebruikt | Gedaan |
| Vereiste reviews die niet te omzeilen zijn | Nul vereiste goedkeuringen | Bewust niet: één beheerder |
| Ondertekende commits | Niet vereist | Open |
| Geïsoleerde runners, geen `--privileged` | Runners van GitHub; geen `--privileged` | Gedaan |
| Geheimen weg uit images | Geen geheimen in de image (A-12) | Gedaan |
| Artefacten ondertekenen (Sigstore) | Niet | Open |

## 10. Vulnerable Dependency Management

| Aanbeveling | In de app | Status |
|---|---|---|
| Vanaf het begin automatisch analyseren | Dependabot en Trivy | Gedaan |
| Een tool met onderdrukking van valse meldingen | Trivy met een VEX (MIT-41) | Gedaan |
| Per lek een besluit van wie het risico draagt | `vex/README.md`: bijwerken, verwijderen, afschermen, of een verklaring met reden; jij beslist | Gedaan |
| Een fix testen die vóór faalt en erna slaagt | Elke maatregel heeft een test met een T-nummer | Gedaan |
| Geen fix: alternatieven en workarounds zoeken | Verwijderen uit de image (pip), een mitigatie met een verklaring (mount), of een verklaring dat de code er niet is (libpq5, T-146) | Gedaan |
| Een alert alleen voor die ene CVE onderdrukken | Een verklaring per CVE en per versie | Gedaan |
| De tijdelijke mitigatie documenteren | In `vex/README.md` en in de verklaring zelf | Gedaan |

## 11. Dependency Graph SBOM

| Aanbeveling | In de app | Status |
|---|---|---|
| Een standaardformaat, zoals CycloneDX | CycloneDX 1.7 (MIT-36) | Gedaan |
| OS-pakketten en meegeleverde bibliotheken, niet alleen manifesten | Debian- en Python-pakketten uit de image; wat buiten dpkg en pip om zit, mist (T-118) | Deels |
| Automatisch na het oplossen van de afhankelijkheden, afgestemd op de image | Uit de gebouwde image, bij elke build | Gedaan |
| Elke release een eigen inventaris | Een SBoM per run, 90 dagen bewaard | Gedaan |
| De uitgever van de VEX controleren, en de integriteit | De VEX staat in de repo en wijzigt alleen via een pull request; hij is niet ondertekend | Deels |
| De SBoM aan de digest van de image binden met een ondertekende attestation | Niet | Open |
| Bij een nieuw advies opnieuw beoordelen | Bij de volgende pull request; een dagelijkse scan is gepland (Week 8, stap 6) | Gepland |
| Een nieuwe SBoM vergelijken met die van de vorige release | Niet | Open |

## 12. Abuse Case

Je misuse cases (`entries.md`) naast wat een goede abuse case bevat.

| Wat erin hoort | In de BoK | Status |
|---|---|---|
| Een uniek ID | MC-01 tot MC-31 | Gedaan |
| De functie die het raakt | "Gerelateerde use case" | Gedaan |
| Een beschrijving van de aanval | De stappen, met OR en AND | Gedaan |
| Een verwijzing naar een aanvalsdatabase (CAPEC) | Niet | Bewust niet: de aanvallen zijn specifiek voor de app |
| Het zakelijke risico, met reden | Kans × Impact, met "Waarom" in de risicomatrix | Gedaan |
| CVSS bij een bekende kwetsbaarheid | Niet gebruikt; een eigen schaal van 3 bij 3 | Bewust niet: CVSS meet ernst, geen risico voor deze app |
| Technisch of zakelijk | Niet onderscheiden | Bewust niet: elke misuse case heeft een technische stap en een gevolg |
| Het ID van de maatregel | MIT-nummers | Gedaan |
| De beslissing: aanpakken of risico accepteren, met reden | Status en Restrisico per misuse case | Gedaan |
| De maatregel als eis, en getest | Een test per misuse case (T-nummers) | Gedaan |

## 13. Threat Modeling

| Aanbeveling | In de app | Status |
|---|---|---|
| Wat bouwen we? Een datastroomdiagram met grenzen | Onderdelen, datastromen en trust boundaries (`BoK/Architecture`, Figuur 2) | Gedaan |
| Wat kan misgaan? | 31 misuse cases; in het verslag met een STRIDE-categorie per dreiging als controle | Gedaan |
| Wat doen we eraan? Mitigeren, elimineren, overdragen of accepteren | 48 maatregelen, en per misuse case een restrisico of een besluit | Gedaan |
| Hebben we het goed genoeg gedaan? | Tests, en de risicomatrix na de maatregelen | Gedaan |
| Vroeg beginnen en bijhouden | Achterwaarts: de misuse case ontstaat met de feature (5.1.1) | Gedaan |
| Aanvalsbomen voor de belangrijkste doelen | Drie bomen (5.1.5) | Gedaan |
| LINDDUN voor privacydreigingen | Niet; privacy staat in de AVG-beoordeling | Bewust niet |

## Voorstellen

Uit de tabellen komt dit, op volgorde van wat het meeste oplevert voor de moeite. Nog niet besloten.

1. **`authz_fail` en `input_validation_fail` loggen** (Logging Vocabulary). Een aanvaller die nummers raadt (MC-02) laat nu geen enkel
   spoor in de log. Eén regel per soort, met een test.
2. **Een time-out bij inactiviteit** (Session Management). Nu is er alleen een absolute van 8 uur.
3. **Het voorvoegsel `__Host-` voor de cookie, en `Clear-Site-Data` bij uitloggen.** Het voorvoegsel eist `Secure`, dus de naam moet
   afhangen van `HTTPS_ONLY` (lokaal draait de app op HTTP).
4. **De image en de SBoM ondertekenen, met provenance** (Supply Chain, CI CD, Dependency Graph SBOM, IaC, Docker #13). De
   attestations van GitHub zijn het kleinste begin; controleren vóór het uitrollen.
5. **Een linter voor het Dockerfile in de check** (Docker #9).
6. **De open containerinstellingen** (Docker #3, #4, #8): al Week 8, stap 10.
7. **Bij het eigen domein**: het `asuid`-record bewaren, en `deployment.py undo` laten waarschuwen dat de `CNAME` eerst weg moet.
8. **Een alert op wijzigingen aan rollen in Azure**, in de activiteitenlog (IaC, Workload Identity).

## Bronnen

Opgehaald op 13-11-2026. Alle sheets: OWASP Cheat Sheet Series, https://cheatsheetseries.owasp.org/cheatsheets/

- `Infrastructure_as_Code_Security_Cheat_Sheet.html`
- `Subdomain_Takeover_Prevention_Cheat_Sheet.html`
- `Workload_Identity_Federation_Cheat_Sheet.html`
- `Docker_Security_Cheat_Sheet.html`
- `Logging_Vocabulary_Cheat_Sheet.html`
- `Session_Management_Cheat_Sheet.html`
- `Cookie_Theft_Mitigation_Cheat_Sheet.html`
- `Software_Supply_Chain_Security_Cheat_Sheet.html`
- `CI_CD_Security_Cheat_Sheet.html`
- `Vulnerable_Dependency_Management_Cheat_Sheet.html`
- `Dependency_Graph_SBOM_Cheat_Sheet.html`
- `Abuse_Case_Cheat_Sheet.html`
- `Threat_Modeling_Cheat_Sheet.html`
