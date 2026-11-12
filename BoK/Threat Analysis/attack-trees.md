# Attack trees

Drie bomen, afgeleid uit de misuse cases in `entries.md`. De indeling volgt het veld "Aanvaller" van de misuse case: waar komt de
aanvaller binnen? Zo staat elke misuse case in één boom, en overlappen de bomen niet.

1. **Boom 1, de applicatie:** wat een bezoeker, een ingelogde gebruiker of een andere website kan doen. Het gevolg is voor
   gebruikers: hun account, hun notities of hun toegang tot de dienst.
2. **Boom 2, het systeem en de beheerketen:** wat iemand met toegang tot de database, een backup, de afhankelijkheden, de pipeline of
   Azure kan doen. Hier zit ook wat een aanvaller doet nadat hij de app heeft overgenomen.
3. **Boom 3, onopgemerkt blijven:** geen eigen doel maar een voorwaarde die bij elke aanval kan horen.

MC-12, MC-13 en MC-29 hebben dezelfde stappen en dezelfde maatregel (MIT-16), en staan daarom als één tak getekend. Een stap die bij de andere boom hoort, staat als verwijzing tussen haakjes ("zie boom 2"), niet nog een keer uitgewerkt. Wie het
account van een gebruiker overneemt (boom 1), kan ook zijn notities lezen.

Zo lees je ze:

- Elke regel is één stap van de aanvaller, kort en in gewone woorden.
- `OR`: een van de takken is genoeg. `AND`: alle takken zijn nodig.
- `[MIT-xx]` achter een stap: deze stap is tegengehouden. `deels`: niet helemaal. `[open]`: nog geen maatregel.
- Een maatregel achter een regel met `AND` eronder is de maatregel die van één stap meer stappen maakt (bijvoorbeeld de versleuteling,
  die naast de gegevens ook de sleutel eist). De stappen eronder houden hun eigen maatregel.
- Elke maatregel staat alleen bij een stap die in de entry van de misuse case onder "Mitigaties" aan hem is toegewezen.

## Boom 1: aanvallen op de applicatie

```
Gebruikers aantasten via de app
  OR  Account overnemen
        OR  Inloggen als het slachtoffer
              AND wachtwoord kennen
                    OR  uit de database halen (MC-01, zie boom 2)                                 [MIT-19, deels]
                          AND hash lezen (zie boom 2)                                             [open]
                          AND wachtwoord raden, 19 MiB per gok                                    [MIT-19, MIT-13]
                    OR  raden of stuffing (MC-03, MC-09)                                          [MIT-10, MIT-13, deels]
              AND code uit de authenticator-app kennen (2FA verplicht)                            [MIT-05, MIT-12]
                    OR  code raden (MC-15)                                                        [MIT-06]
                    OR  onderschepte code meteen gebruiken (MC-16)                                [open]
                    OR  onderschepte code later gebruiken (MC-16)                                 [MIT-07]
                    OR  TOTP-geheim buitmaken (MC-17)
                          OR  meekijken bij het instellen                                         [MIT-08, deels]
                          OR  uit een cache halen                                                 [MIT-08]
                          OR  uit de database ontsleutelen (zie boom 2)                           [MIT-17, deels]
                    OR  herstelcode gebruiken (MC-19)                                             [MIT-11, deels]
        OR  Wachtwoord vergeten misbruiken (MC-21)                                                [MIT-14, deels]
              AND gebruikersnaam kennen (MC-09)                                                   [MIT-14, MIT-30, deels]
              AND herstelcode hebben                                                              [MIT-11, deels]
              AND geldige code uit de app                                                         [MIT-06, MIT-07, deels]
        OR  Zelf 2FA instellen op een account zonder 2FA (MC-20)                                  [open; MIT-12 verkleint het venster]
        OR  Sessiecookie hebben (MC-04)
              OR  meelezen op het netwerk                                                         [lokaal open; op Azure MIT-40, MIT-23]
              OR  kopiëren van een gedeelde browser                                               [MIT-09, MIT-29, deels]
              OR  cookie zelf ondertekenen                                                        [open]
        OR  Via een andere site handelen (CSRF, MC-05)                                            [MIT-20, MIT-23]
        OR  Laten klikken in een onzichtbaar frame (MC-24)                                        [MIT-21]
        OR  Wachtwoord, 2FA of account wijzigen met zijn sessie (MC-12, 13, 29)   [MIT-16, deels]
              AND sessie van het slachtoffer (MC-04, MC-05)
              AND huidig wachtwoord (MC-01, MC-03)
              AND code uit zijn app (MC-15 tot MC-17)
  OR  Notities aantasten
        OR  Andermans notitie-id invullen (MC-02)                                                 [MIT-15]
        OR  Open functie zonder login bereiken (MC-25)                                            [MIT-24]
        OR  SQL-injectie (MC-06)                                                                  [MIT-02]
        OR  Script in een notitie (MC-07)                                                         [MIT-01, MIT-21]
        OR  Gedeelde computer, na de vorige gebruiker (MC-27)
              OR  Terug drukken na uitloggen                                                      [MIT-28]
              OR  sessie die nog openstaat                                                        [MIT-29, deels]
  OR  Dienst hinderen
        OR  Overbelasten met verzoeken (MC-10)
              OR  te lange titel of notitie                                                       [MIT-04]
              OR  groot verzoek                                                                   [MIT-22]
              OR  veel accounts of notities aanmaken                                              [MIT-30, deels]
        OR  Ontwikkelserver van Flask overbelasten (MC-14)                                        [MIT-26]
        OR  Gebruiker buitensluiten met de blokkade (MC-18)                                       [open]
```

## Boom 2: aanvallen op het systeem en de beheerketen

```
Systeem of beheer compromitteren
  OR  Gegevens uit de opslag halen
        OR  Notities lezen (MC-23)                                                                [MIT-18, deels]
              AND database, volume of backup lezen (MC-23)                                        [open]
              AND gegevenssleutel hebben (MC-22)                                                  [MIT-32, deels; op Azure in Key Vault]
        OR  TOTP-geheimen lezen (MC-17)                                                           [MIT-17, deels]
              AND database, volume of backup lezen (MC-17)                                        [open]
              AND gegevenssleutel hebben (MC-22)                                                  [MIT-32, deels; op Azure in Key Vault]
        OR  Wachtwoorden lezen en raden (MC-01)                                                   [MIT-19, deels]
              AND database, volume of backup lezen (MC-01)                                        [open]
              AND wachtwoord raden, 19 MiB per gok                                                [MIT-19, MIT-13]
  OR  App of code overnemen
        OR  Via een afhankelijkheid (MC-11)
              OR  bekende kwetsbaarheid in een pakket                                             [MIT-33, MIT-35, MIT-39, MIT-41, deels]
              OR  kwaadaardige nieuwe pakketversie                                                [MIT-03]
              OR  kwetsbaarheid in de basisimage                                                  [MIT-33, MIT-35, MIT-39, MIT-41, deels]
              OR  image-tag die naar een andere image wijst                                       [MIT-03]
              OR  kwetsbaarheid die de scan niet ziet (psycopg-binary)                            [MIT-43, deels]
        OR  Eigen code laten uitrollen via de pipeline (MC-30)                                    [MIT-33, MIT-34, MIT-39, MIT-44, deels]
  OR  Na overname van de app
        OR  Gegevenssleutel uit de app halen (MC-22)                                              [MIT-32, deels; op Azure in Key Vault]
        OR  Root worden in de container (MC-14)                                                   [MIT-26, MIT-42]
        OR  Alle rijen lezen of wissen met de rechten van de app (MC-08)                          [open]
        OR  Database weggooien (MC-08)                                                            [MIT-27]
  OR  Azure overnemen (MC-31)
        OR  Azure-login van de beheerder stelen                                                   [open; de tenant vraagt een tweede stap]
        OR  az login-sessie op de pc van de beheerder gebruiken                                   [open]
        OR  Terraform-state wijzigen of wissen                                                    [MIT-38, deels: een Owner geeft zich een rol]
        OR  Terraform-state lezen met een accountsleutel                                          [MIT-38]
```

## Boom 3: onopgemerkt blijven

```
Onopgemerkt aanvallen (MC-28)
  AND een aanval uitvoeren (boom 1 of boom 2)
  AND niet live opgemerkt worden                                                                  [MIT-37, deels: alleen een mail bij een blokkade]
  AND geen spoor achterlaten                                                                      [MIT-31, deels]
        OR  log wissen met beheer over de host                                                    [lokaal open; op Azure MIT-31]
        OR  valse logregels (MC-26)                                                               [MIT-25]
```
