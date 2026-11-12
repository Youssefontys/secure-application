# Attack trees

Per aanvallersdoel een boom, afgeleid uit de misuse cases in `entries.md`.

Zo lees je ze:

- Elke regel is één stap van de aanvaller, in gewone woorden. Verwijzingen naar andere bomen staan tussen haakjes, niet als stap.
- `OR`: een van de takken is genoeg. `AND`: alle takken zijn nodig.
- `[MIT-xx]` achter een stap: deze stap is tegengehouden. `deels`: niet helemaal. `[open]`: nog geen maatregel.
- Een maatregel achter een regel met `AND` eronder is de maatregel die van één stap meer stappen maakt (bijvoorbeeld de versleuteling,
  die naast de gegevens ook de sleutel eist). De stappen eronder houden hun eigen maatregel.
- Elke maatregel staat alleen bij een stap die in de entry van de misuse case onder "Mitigaties" aan hem is toegewezen.

## Doel 1: notities van een andere gebruiker lezen, wijzigen of vernietigen

```
Notities van een ander lezen, wijzigen of vernietigen
  OR  Met een eigen account andermans notitie-id invullen (opeenvolgende getallen raden, MC-02)   [MIT-15]
  OR  Zonder login een functie bereiken die open is gelaten (MC-25)                              [MIT-24]
  OR  Notities uit de database lezen, die versleuteld zijn opgeslagen (MC-23, MC-08)              [MIT-18, deels]
        AND de versleutelde gegevens binnenhalen                                                  [open]
              OR  met een query met de rechten van de app (lezen mag die nog, MC-08)
              OR  het volume of een backup lezen
        AND de gegevenssleutel hebben (MC-22)                                                     [MIT-32, deels; op Azure in Key Vault]
  OR  Eigen code laten uitrollen, die de sleutel dan heeft (MC-30)                                [MIT-33, MIT-34, MIT-39, MIT-44, deels]
  OR  De app overnemen, die de sleutel heeft (MC-11)
        OR  een bekende kwetsbaarheid in een Python-pakket die niet is bijgewerkt                 [MIT-33, MIT-35, MIT-39, MIT-41, deels]
        OR  een kwaadaardige nieuwe pakketversie                                                  [MIT-03]
        OR  een kwetsbaarheid in de basisimage, zoals een Debian-bibliotheek                      [MIT-33, MIT-35, MIT-39, MIT-41, deels]
        OR  een image-tag die naar een andere image wijst                                         [MIT-03]
        OR  een kwetsbaarheid in code die de scan niet ziet, zoals de bibliotheken van psycopg-binary   [MIT-43, deels]
  OR  Via SQL-injectie gegevens uit de database lezen of wijzigen (MC-06)                         [MIT-02]
  OR  Een script in een notitie laten uitvoeren (MC-07)                                           [MIT-01, MIT-21]
  OR  Op een gedeelde computer de notities openen na de vorige gebruiker (MC-27)
        OR  na het uitloggen op Terug drukken                                                     [MIT-28]
        OR  een sessie gebruiken waaruit niet is uitgelogd                                        [MIT-29, deels]
  OR  Het account van het slachtoffer verwijderen, met de notities erin (MC-13)                   [MIT-16, deels]
        AND een sessie van het slachtoffer hebben (zie doel 2)
        AND het huidige wachtwoord van het slachtoffer kennen (zie doel 2)
        AND een code uit de authenticator-app van het slachtoffer hebben (zie doel 2)
  OR  Het account van het slachtoffer overnemen en zijn notities lezen (zie doel 2)
```

## Doel 2: als een andere gebruiker handelen (account overnemen)

```
Als het slachtoffer handelen: het account overnemen, of een handeling afdwingen
  OR  Inloggen als het slachtoffer
        AND het wachtwoord kennen
              OR  het uit de database halen (MC-01)                                               [MIT-19, deels]
                    AND de hash lezen                                                             [open]
                    AND het wachtwoord raden, 19 MiB per gok per account                          [MIT-19, MIT-13]
              OR  raden of stuffing met een bekende gebruikersnaam (MC-03, MC-09)                 [MIT-10, MIT-13, deels]
        AND de code uit de authenticator-app kennen (tweestapsverificatie is verplicht)           [MIT-05, MIT-12]
              OR  de code raden (MC-15)                                                           [MIT-06]
              OR  een onderschepte code meteen gebruiken (MC-16)                                  [open]
              OR  een onderschepte code later gebruiken (MC-16)                                   [MIT-07]
              OR  het TOTP-geheim buitmaken (MC-17)
                    OR  het versleutelde geheim uit de database lezen en ontsleutelen                 [MIT-17, deels]
                          AND de database, het volume of een backup lezen                         [open]
                          AND de gegevenssleutel hebben (MC-22)                                   [MIT-32, deels; op Azure in Key Vault]
                    OR  meekijken tijdens het instellen van de tweede factor                      [MIT-08, deels]
                    OR  de instelpagina of de QR-code uit een cache halen                         [MIT-08]
              OR  de herstelcode gebruiken (MC-19)                                                [MIT-11, deels]
  OR  Een nieuw wachtwoord instellen via wachtwoord vergeten (MC-21)                              [MIT-14, deels]
        AND de gebruikersnaam kennen (MC-09)                                                      [MIT-14, MIT-30, deels]
        AND de herstelcode hebben                                                                 [MIT-11, deels]
        AND een geldige code uit de app hebben                                                    [MIT-06, MIT-07, deels]
  OR  Zelf een tweede factor instellen op een account dat er nog geen heeft, met het wachtwoord (MC-20)   [open; MIT-12 verkleint het venster]
  OR  De sessiecookie van het slachtoffer hebben (MC-04)
        OR  meelezen op het netwerk (lokaal geen TLS)                                             [lokaal open; op Azure MIT-40, MIT-23]
        OR  kopiëren van een gedeelde browser                                                     [MIT-09 na uitloggen, MIT-29 na 8 uur, deels]
        OR  zelf een cookie ondertekenen met de sessiesleutel                                     [open]
  OR  Via een andere site handelen met de cookie van het slachtoffer (MC-05)                      [MIT-20, MIT-23]
  OR  Het slachtoffer laten klikken in een onzichtbaar frame (MC-24)                              [MIT-21]
  OR  Het wachtwoord van het slachtoffer wijzigen (MC-12)                                         [MIT-16, deels]
        AND een sessie van het slachtoffer hebben (MC-04, MC-05)
        AND het huidige wachtwoord kennen (MC-01, MC-03)
        AND een code uit de authenticator-app hebben (MC-15 tot MC-17)
  OR  De tweede factor van het slachtoffer vervangen door een eigen telefoon (MC-29)              [MIT-16]
        AND een sessie van het slachtoffer hebben (MC-04)
        AND één code uit zijn app hebben (MC-16)
        AND het huidige wachtwoord kennen (MC-01, MC-03)
```

## Doel 3: de dienst onbruikbaar maken

```
De dienst onbruikbaar maken
  OR  Zeer grote of veel verzoeken sturen (MC-10)
        OR  een te lange titel of notitie opslaan                                                 [MIT-04]
        OR  een groot verzoek sturen dat eerst helemaal wordt ingelezen                           [MIT-22]
        OR  veel accounts (elk een Argon2id-hash) of notities aanmaken                            [MIT-30, deels]
  OR  De ontwikkelserver van Flask overbelasten (MC-14)                                           [MIT-26]
  OR  Een gebruiker buitensluiten door de blokkade voor zijn account te laten lopen (MC-18)       [open]
  OR  De app overnemen en de gegevens vernietigen (MC-08, na overname, zie doel 1)
        OR  de database weggooien                                                                 [MIT-27]
        OR  alle rijen wissen met de rechten van de app                                           [open]
```

## Doel 4: aanvallen zonder spoor

```
Een aanval uitvoeren zonder dat iemand het merkt en zonder spoor achteraf (MC-28)
  AND een aanval uitvoeren (raden, CSRF, rijen wijzigen, massaal aanmaken)
  AND niet live opgemerkt worden: hopen dat niemand meekijkt                                      [MIT-37, deels: alleen een mail bij een blokkade]
  AND geen spoor achterlaten                                                                      [MIT-31, deels]
        OR  het log wissen, met beheer over de host of de container                               [lokaal open; op Azure MIT-31]
        OR  valse regels in het log zetten om een spoor te verbergen (MC-26)                      [MIT-25]
```

## Doel 5: de omgeving op Azure overnemen

```
Alles op Azure in handen krijgen (MC-31)
  OR  De Azure-login van de beheerder stelen                                                      [open; de tenant vraagt een tweede stap]
  OR  Een geldige az login-sessie op de pc van de beheerder gebruiken                             [open]
  OR  De Terraform-state wijzigen of wissen, zodat de volgende apply iets anders doet                                                       [MIT-38, deels: een Owner geeft zich een rol]
  OR  De state lezen met een accountsleutel, buiten de rollen om                                  [MIT-38]
  OR  Eigen code laten uitrollen via de pipeline (MC-30)                                          [MIT-33, MIT-34, MIT-39, MIT-44, deels]
```
