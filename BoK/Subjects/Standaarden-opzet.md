# Standaarden: opzet in twee delen

Opzet van hoofdstuk 4 (Standards) van de BoK. De uitgewerkte tekst staat in het rapport (paragraaf 4.1 tot en met 4.3, met een
regel "Standaard:" in elke paragraaf van 5.2 en 5.3); dit bestand is de opzet waaruit het ontstond. Wat tussen `[ ]` staat of als
"te checken" is gemarkeerd, is bij de opzet niet aan een bron getoetst.

Wat de uitwerking anders doet dan deze opzet:

- De CCM v4 en de MCSB zijn twee kaders naast elkaar, geen keten: de MCSB-controls verwijzen niet naar de CCM. Ze verwijzen wel
  naar de CIS **Controls**, niet naar de CIS **Benchmarks**, en Microsoft zegt zelf dat zo'n koppeling geen volledige naleving betekent.
- Threat modelling, security design en de SBoM staan onder compliance (4.1), omdat de wetten ze eisen (NIS2 artikel 21, de CRA, AVG
  artikel 25).
- De omgekeerde tabel (maatregel naar control) is vervallen: de controls staan als regel "Standaard:" bij elke maatregel in 5.2 en 5.3.
- Acht CCM-domeinen zijn gemarkeerd, niet zes.
- Het Azure-deel van het oude hoofdstuk (CAF, landing zones, Azure Policy) is gekort tot een alinea: voor één app te groot, en niet gebouwd.

## De indeling

| Deel | Vraag | Standaarden |
|---|---|---|
| **A. Compliance** | Welke standaard helpt me een wet na te leven? | NIS2: ISO/IEC 27001. AVG: ISO/IEC 27701. CRA: de EN 40000-reeks. IEC 62443 (OT): niet van toepassing |
| **B1. Security design, applicatie** | Hoe bouw ik de app veilig? | OWASP Top 10 Proactive Controls (C1 t/m C10) |
| **B2. Security design, systeem en cloud** | Hoe richt ik de omgeving veilig in? | CSA Cloud Controls Matrix v4 (cloud), CIS Benchmarks (systeem), Microsoft Cloud Security Benchmark (Azure) |

Volgorde in de BoK: wetten (hoofdstuk 3) → standaarden A → threat analysis → security design, waar elke maatregel (MIT) naar
een control uit B1 of B2 verwijst. Een standaard uit A zegt *wat* de wet verwacht; B zegt *hoe* je het bouwt.

## Deel A: standaarden die bij een wet horen

Elke regel: de wet uit hoofdstuk 3, de standaard die helpt, en wat dat voor deze app betekent. Standaarden zijn vrijwillig; een
wet schrijft ze niet voor, behalve geharmoniseerde normen, die een vermoeden van conformiteit geven.

| Wet | Standaard | Wat het helpt | Deze app |
|---|---|---|---|
| NIS2 / Cyberbeveiligingswet | ISO/IEC 27001 (met 27002) | Een managementsysteem voor informatiebeveiliging; de maatregelen van NIS2 artikel 21 [te checken: artikelverwijzing] zijn ermee in te vullen | App valt niet onder NIS2 (hoofdstuk 3), dus alleen als voorbeeld van hoe het zou gaan |
| CRA | EN 40000-reeks (geharmoniseerde normen) [te checken: status, waarschijnlijk nog concept] | Zou een vermoeden van conformiteit geven als ze zijn gepubliceerd | CRA geldt niet voor de app (open source, geen handelsactiviteit); de normen zijn dus een verwijzing, geen eis |
| AVG | ISO/IEC 27701 (privacy-uitbreiding op 27001) [te checken] | Een kader voor privacymaatregelen en het verwerkingsregister | Het register en de datalekprocedure (`Datalekprocedure.md`) doen hetzelfde op kleine schaal |
| (OT-systemen) | IEC 62443 | Beveiliging van industriële systemen | Niet van toepassing: de app is geen OT |

Eén zin als conclusie: voor deze app is geen enkele standaard uit A verplicht; ze laten zien welke route een organisatie zou
volgen, en de wetten uit hoofdstuk 3 zijn de eis, niet de standaard.

## Deel B1: applicatie

Dit is wat er nu al staat in 4.1 en 4.2: OWASP Proactive Controls als hoofdnorm, met de tabel BoK-onderwerp → control → wat de
app doet. Dat deel blijft; het wordt alleen B1 genoemd. De omgekeerde tabel komt erbij (zie onder).

## Deel B2: systeem en cloud

Het oude deel (P11 t/m P15) hoort hier, korter:

- **CSA Cloud Controls Matrix v4** voor de cloud: wie doet wat tussen jou en Microsoft, per domein.
- **CIS Benchmarks** voor de configuratie van het systeem: de CIS Microsoft Azure Foundations Benchmark; daarnaast CIS PostgreSQL
  en Docker als ze bij de gebruikte onderdelen passen [te checken: welke benchmark bij Container Apps past].
- **Microsoft Cloud Security Benchmark** als Azure-specifieke vertaling, met het ID per control (NS-1, IM-3, ...).
- CAF, landing zones en Azure Policy: één alinea. Voor één kleine app is het een voorbeeld van hoe een organisatie het afdwingt,
  geen onderdeel van de app.

Wat in het oude deel aangepast moet worden:

1. ISO 27001 en NIST CSF zijn geen "wetgeving"; noem ze normen/frameworks.
2. "In één keer voldaan aan ISO 27001 en NIST" en "100% traceerbaarheid" zijn te sterk; het deel zelf zegt dat een
   MCSB-control geen volledige naleving garandeert.
3. Het is CCM v4, niet "CSF v4"; CSF is van NIST.
4. De inleiding verwijst naar paragraaf 4.3 die niet bestaat.
5. Placeholders opruimen: "Figuur 2/3/5: x", "Opsommingsteken1 t/m 4", "Conclussies: X", "Welke volgorde?".

## De omgekeerde tabel: maatregel → control

Dit is wat in het hoofdstuk Security design terugkomt: bij elke MIT staat de control die hem onderbouwt. Eerste rijen, afgeleid
van de bestaande tabel 4.1; de rest en de CCM/CIS-kolom vul je in.

| Maatregel | OWASP Proactive Control | CCM v4 / CIS / MCSB |
|---|---|---|
| MIT-17, MIT-18 kolomversleuteling | C2 | [in te vullen] |
| MIT-40 TLS 1.2 en 1.3 | C2 | [in te vullen] |
| MIT-19 Argon2id | C2 en C7 | [in te vullen] |
| MIT-05, MIT-12, MIT-14 TOTP en herstel | C7 | [in te vullen] |
| MIT-24 standaard dicht, MIT-15 eigenaarscontrole | C1 | [in te vullen] |
| MIT-02 queries met parameters | C3 | [in te vullen] |
| MIT-31 JSON-log | C9 | [in te vullen] |
| MIT-36 SBoM | C6 | [in te vullen] |

Maatregelen die niet in B1 passen (netwerk, Key Vault, Terraform, back-up) krijgen alleen een regel in B2.
