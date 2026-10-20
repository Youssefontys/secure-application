# Risicomatrix

Per misuse case het risico, als **Risico = Kans × Impact**, op een matrix van 3 bij 3: één keer zonder de
maatregelen van die misuse case, en één keer nu, met wat er gebouwd en uitgerold is (Azure, 18-10-2026). Zo is te
zien wat de maatregelen doen, en wat er overblijft. Ingeschat op 19-10-2026, uit de entries en tests van deze BoK.

## De schalen

**Kans:** hoe makkelijk de aanvallers van deze app dit voor elkaar krijgen. Die aanvallers zijn vooral
medestudenten in de hacking week (gericht, met de URL en een paar dagen tijd) en geautomatiseerde scanners op
internet; een aanvaller met het account of de pc van de beheerder is zeldzamer.

| Kans | Betekenis |
|---|---|
| 1 Laag | Vraagt iets wat die aanvallers normaal niet hebben: het account of de pc van de beheerder, toegang tot de database of de container, of een fout die er nu niet in zit |
| 2 Midden | Lukt met gerichte moeite en kennis van de app, of vraagt iets van het slachtoffer: een klik, een gedeelde computer, hetzelfde netwerk |
| 3 Hoog | Lukt met standaardtools of een script, zonder voorkennis, of gebeurt vanzelf |

**Impact:** wat er misgaat als het lukt, naar de assets in `Architecture/components.md`.

| Impact | Betekenis |
|---|---|
| 1 Laag | Hinder, of informatie zonder directe schade: een bestaande gebruikersnaam, een korte melding |
| 2 Midden | Eén account: inloggen als iemand anders, of de notities van één gebruiker lezen, wijzigen of wissen; of de app een tijd onbruikbaar |
| 3 Hoog | Alle gebruikers of de hele omgeving: alle notities of wachtwoorden, de geheimen, of eigen code op Azure |

**Risico:** 1 en 2 laag, 3 en 4 midden, 6 en 9 hoog.

|  | Impact 1 | Impact 2 | Impact 3 |
|---|---|---|---|
| **Kans 3** | 3 midden | 6 hoog | 9 hoog |
| **Kans 2** | 2 laag | 4 midden | 6 hoog |
| **Kans 1** | 1 laag | 2 laag | 3 midden |

"Zonder maatregelen" betekent: zonder de mitigaties die bij die misuse case staan, en verder de app en Azure zoals ze
zijn. Een voorwaarde die zelf een andere misuse case is, zoals de app overnemen, telt bij de kans mee zoals hij nu is.

## De matrix zonder maatregelen

|  | Impact 1 | Impact 2 | Impact 3 |
|---|---|---|---|
| **Kans 3** | MC-09, MC-26 | MC-03, MC-10, MC-18, MC-21, MC-27, MC-28 | MC-02, MC-06, MC-11 |
| **Kans 2** |  | MC-04, MC-05, MC-07, MC-12, MC-13, MC-15, MC-16, MC-19, MC-20, MC-24, MC-25, MC-29 | MC-30 |
| **Kans 1** |  |  | MC-01, MC-08, MC-14, MC-17, MC-22, MC-23, MC-31 |

10 keer hoog, 21 keer midden, 0 keer laag.

## De matrix nu

|  | Impact 1 | Impact 2 | Impact 3 |
|---|---|---|---|
| **Kans 3** | MC-09 |  |  |
| **Kans 2** |  | MC-10, MC-16, MC-18, MC-27, MC-28 | MC-11 |
| **Kans 1** | MC-23, MC-26 | MC-01, MC-03, MC-04, MC-05, MC-07, MC-12, MC-13, MC-14, MC-15, MC-17, MC-19, MC-20, MC-21, MC-24, MC-25, MC-29 | MC-02, MC-06, MC-08, MC-22, MC-30, MC-31 |

1 keer hoog, 12 keer midden, 18 keer laag.

## Per misuse case

K is kans, I is impact, R is risico.

| MC | Wat | Zonder: K × I = R | Nu: K × I = R | Waarom |
|---|---|---|---|---|
| MC-01 | Wachtwoorden uit de database | 1 × 3 = 3 | 1 × 2 = 2 | Alleen via de database of de app. Als Argon2id-hash kost elke gok 19 MiB (MIT-19); een zwak wachtwoord blijft te raden, en hier is daarna nog de tweede factor nodig |
| MC-02 | Andermans notities | 3 × 3 = 9 | 1 × 3 = 3 | Eerst ging een opeenvolgend id naar elke notitie. Nu geeft andermans notitie 404 (MIT-15); alleen een nieuwe route zonder die controle opent het weer |
| MC-03 | Wachtwoord raden | 3 × 2 = 6 | 1 × 2 = 2 | Limieten per adres en per account (MIT-10), en een geraden wachtwoord geeft alleen een halve login (MIT-05, MIT-12) |
| MC-04 | Sessiecookie stelen | 2 × 2 = 4 | 1 × 2 = 2 | Op Azure alleen over HTTPS (MIT-40, MIT-23, MIT-21), hooguit 8 uur (MIT-29) en ongeldig na uitloggen (MIT-09). Lokaal zonder TLS |
| MC-05 | CSRF | 2 × 2 = 4 | 1 × 2 = 2 | Een token op elke POST (MIT-20) en `SameSite=Lax` (MIT-23) |
| MC-06 | SQL-injectie | 3 × 3 = 9 | 1 × 3 = 3 | Overal parameters (MIT-02). Lukt het toch, dan kan de rol van de app alle rijen lezen en wijzigen (MC-08) |
| MC-07 | Opgeslagen XSS | 2 × 2 = 4 | 1 × 2 = 2 | Escapen (MIT-01), een strenge CSP als tweede laag (MIT-21), en een gebruikersnaam zonder HTML (MIT-22) |
| MC-08 | Te veel databaserechten | 1 × 3 = 3 | 1 × 3 = 3 | Eerst de eigenaar van de database, nu een eigen rol (MIT-27): geen tabellen of rollen meer, maar nog wel alle rijen. Kleiner, maar nog steeds alle gebruikers |
| MC-09 | Gebruikersnamen opsporen | 3 × 1 = 3 | 3 × 1 = 3 | Registreren zegt of een naam bezet is. Sinds 5d0f1d0 telt ook een bezette naam mee voor de limiet van 10 per uur per adres (MIT-30); vanaf veel adressen blijft het makkelijk |
| MC-10 | Overbelasten | 3 × 2 = 6 | 2 × 2 = 4 | Een grens per verzoek, per veld en op registreren en notities (MIT-22, MIT-04, MIT-30); vanaf veel adressen tegelijk, met Argon2id per poging, lukt het nog |
| MC-11 | Kwetsbare afhankelijkheid | 3 × 3 = 9 | 2 × 3 = 6 | Vastgezet (MIT-03), Dependabot (MIT-33), een scan bij elke pull request en vóór het publiceren (MIT-35, MIT-39), en een beslissing per lek, ook zonder oplossing (MIT-41). Een lek dat na de build bekend wordt, gaat door tot de volgende pull request, een draaiende image wordt niet opnieuw gescand, een verklaring in de VEX kan fout zijn, en de OpenSSL in `cryptography` en Python zelf ziet de scan niet (T-118); de bibliotheken van psycopg-binary zijn sinds MIT-43 weg |
| MC-12 | Wachtwoord wijzigen met andermans sessie | 2 × 2 = 4 | 1 × 2 = 2 | Het huidige wachtwoord en een code (MIT-16) |
| MC-13 | Andermans account verwijderen | 2 × 2 = 4 | 1 × 2 = 2 | Wachtwoord en code (MIT-16); verwijderen blijft onomkeerbaar |
| MC-14 | Root en de ontwikkelserver | 1 × 3 = 3 | 1 × 2 = 2 | Gunicorn als gewone gebruiker zonder schrijfrecht op de code (MIT-26), en geen setuid-programma's om alsnog root te worden (MIT-42); wat de app mag, blijft (MC-08, MC-22) |
| MC-15 | De code raden | 2 × 2 = 4 | 1 × 2 = 2 | Een verdubbelende blokkade (MIT-06): ongeveer 0,56% kans in een jaar |
| MC-16 | Een code onderscheppen | 2 × 2 = 4 | 2 × 2 = 4 | Elke code één keer (MIT-07) en TLS op Azure (MIT-40), maar een nepsite die meteen doorgeeft, komt binnen; alleen WebAuthn of passkeys helpen |
| MC-17 | Het TOTP-geheim buitmaken | 1 × 3 = 3 | 1 × 2 = 2 | Versleuteld (MIT-17): uit de database alleen met de sleutel; meekijken tijdens het instellen blijft |
| MC-18 | Buitensluiten met de blokkade | 3 × 2 = 6 | 2 × 2 = 4 | Alleen per adres, nooit een account over alle adressen (MIT-10). Op een gedeeld netwerk, zoals op school in de hacking week, wel; de hackmode verkleint dat |
| MC-19 | De herstelcode | 2 × 2 = 4 | 1 × 2 = 2 | 128 bits, een blokkade, alleen de SHA-256 en `no-store` (MIT-11) |
| MC-20 | De eerste instelling kapen | 2 × 2 = 4 | 1 × 2 = 2 | Tweestapsverificatie verplicht, en een nieuw account gaat direct naar het instellen (MIT-12); het korte venster blijft |
| MC-21 | Wachtwoord vergeten misbruiken | 3 × 2 = 6 | 1 × 2 = 2 | Twee van de drie factoren: herstelcode en code (MIT-14) |
| MC-22 | De gegevenssleutel | 1 × 3 = 3 | 1 × 3 = 3 | Op Azure in Key Vault, en alleen de identiteit van de app leest hem (AZ-10, T-86); lokaal `.env` alleen voor de eigenaar (MIT-32). De draaiende app heeft hem wel, dus wie die overneemt, ook |
| MC-23 | Notities uit de database | 1 × 3 = 3 | 1 × 1 = 1 | Versleuteld (MIT-18): zonder de sleutel alleen hoeveel notities en wanneer |
| MC-24 | Clickjacking | 2 × 2 = 4 | 1 × 2 = 2 | De browser laadt de app niet in een frame (MIT-21) |
| MC-25 | Een vergeten route | 2 × 2 = 4 | 1 × 2 = 2 | Elke route standaard dicht, en de securitytest bewaakt de lijst (MIT-24, T-80) |
| MC-26 | Een fout uitlokken | 3 × 1 = 3 | 1 × 1 = 1 | Een korte melding, en geen regeleinde in de log (MIT-25) |
| MC-27 | De gedeelde computer | 3 × 2 = 6 | 2 × 2 = 4 | Geen pagina in de cache (MIT-28) en hooguit 8 uur (MIT-29); wie niet uitlogt, laat de sessie toch open voor de volgende |
| MC-28 | Onopgemerkt blijven | 3 × 2 = 6 | 2 × 2 = 4 | Elke gebeurtenis in de log, op Azure 30 dagen buiten bereik van de app (MIT-31), en een mail bij een blokkade (MIT-37); andere aanvallen geven geen mail |
| MC-29 | De tweede factor vervangen | 2 × 2 = 4 | 1 × 2 = 2 | Ook het huidige wachtwoord (MIT-16) |
| MC-30 | Eigen code via de pipeline | 2 × 3 = 6 | 1 × 3 = 3 | Eerst een token met `write:packages` dat weken gold. Nu het token van de run met minimale rechten, actions op een commit, en alleen via een pull request met een check (MIT-34, MIT-39); uitrollen vanuit GitHub zonder sleutel en pas na goedkeuring (MIT-44); het account van de beheerder blijft de sleutel |
| MC-31 | Azure via de beheerder | 1 × 3 = 3 | 1 × 3 = 3 | De state alleen via Entra ID, zonder accountsleutels (MIT-38), en de tenant vraagt een tweede stap; maar de beheerder is Owner, dus wie zijn login heeft, kan alles |

## Wat er overblijft, en wat ermee gebeurt

- **Hoog: MC-11, een kwetsbare afhankelijkheid (6).** De enige hoge. De scan houdt elk bekend lek van HIGH of
  CRITICAL tegen tot er een beslissing is, ook zonder oplossing (MIT-41, deelvraag 2 van het onderzoek). Maar hij
  ziet geen lek dat pas na de build bekend wordt, en de draaiende image wordt niet opnieuw gescand. En volgens
  deelvraag 3 ziet hij niets van wat buiten dpkg en pip om in de image zit: 52 van de 70 bestanden die de app
  laadt (T-118). Sinds MIT-43 komt libpq uit Debian, maar Python zelf en de OpenSSL in `cryptography` blijven
  buiten zicht. Daarom blijft de kans 2. Besluit: verder verkleinen: de bewaarde SBoM opnieuw scannen,
  bijvoorbeeld elke dag.
- **Midden, met impact 3: MC-02, MC-06, MC-08, MC-22, MC-30, MC-31.** Weinig kans, maar als het lukt, zijn alle
  gebruikers of de hele omgeving geraakt. MC-02 en MC-06 rusten elk op één regel in elke route; de securitytest
  bewaakt ze. MC-08 en MC-22 komen neer op wie de app overneemt: de app heeft de sleutel en de rechten nodig om te
  werken. MC-30 en MC-31 komen neer op de accounts van de beheerder, met tweestapsverificatie. Besluit: accepteren,
  met de lagen die er zijn.
- **Midden, met kans 2: MC-10, MC-16, MC-18, MC-27, MC-28.** Waarschijnlijker, maar één account of een tijdje
  onbruikbaar. MC-18 telt in de hacking week, met een klas achter één adres; daarvoor is de hackmode. MC-16 lost
  alleen een factor op die aan het domein vastzit, zoals passkeys. MC-28: alleen een blokkade geeft een mail.
  Besluit: accepteren voor deze app; passkeys en meer alerts zijn een volgende stap.
- **Midden: MC-09, gebruikersnamen opsporen (3).** Bij zelfgekozen namen niet te voorkomen, en de impact is laag.
  Besluit: accepteren.

## Keuzes

- **3 bij 3, niet 5 bij 5.** De docent vraagt 3x3 of 3x5. Met drie stappen is elke score uit te leggen met één zin
  uit de entries; een 5x5 suggereert een precisie die er niet is.
- **Zonder en met maatregelen.** Een matrix van alleen nu laat niet zien waarom iets laag scoort; de twee samen
  laten zien wat de maatregelen deden.
- **Kans naar de echte aanvallers.** Medestudenten in de hacking week en scanners, niet een staat met onbeperkte
  middelen. Een aanvaller met het account van de beheerder staat apart, in MC-30 en MC-31.
