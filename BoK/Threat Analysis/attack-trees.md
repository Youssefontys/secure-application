# Attack trees

Per aanvallersdoel een boom, afgeleid uit de misuse cases in `entries.md`.
`OR` = een van de takken is genoeg. `AND` = alle takken zijn nodig.
`[MIT-xx]` = deze tak is tegengehouden. `[open]` = nog geen maatregel.

## Doel 1: notities van een andere gebruiker lezen of vernietigen

```
Notities van een ander lezen of wijzigen
  OR  Via een eigen account andermans notitie-id invullen (MC-02)        [MIT-15]
        AND eigen account aanmaken en inloggen
        AND notitie-id raden (opeenvolgende getallen)
  OR  De database direct lezen (MC-23, MC-08)                             [MIT-18, deels]
        AND de database lezen                                              [open]
              OR  rechtstreekse query met de eigenaarrol
              OR  het volume of een backup lezen
        AND de gegevenssleutel hebben (MC-22)                              [open]
  OR  De app overnemen, die de sleutel heeft (MC-11)
        OR  bekende kwetsbaarheid, niet bijgewerkt                         [open]
        OR  kwaadaardige nieuwe pakketversie                               [MIT-03]
        OR  kwetsbaarheid of andere image achter de tag                    [open]
  OR  Script in een notitie laten uitvoeren (MC-07)                       [MIT-01, MIT-21]
  OR  Het hele account van het slachtoffer verwijderen (MC-13)            [MIT-16, deels]
        AND handelen als het slachtoffer (cookie van MC-04, of via MC-05)
        AND het wachtwoord kennen (MC-01, MC-03)
  OR  Als de gebruiker handelen (zie doel 2)
```

## Doel 2: als een andere gebruiker handelen (account overnemen)

```
Account overnemen
  OR  Inloggen als het slachtoffer
        AND het wachtwoord kennen
              OR  uit de database halen (MC-01)                            [MIT-19, deels]
                    AND de hash lezen                                      [open]
                    AND het wachtwoord raden, 19 MiB per gok per account   [MIT-19, MIT-13]
              OR  raden of stuffing (MC-03)                                [MIT-10, MIT-13, deels]
                    AND gebruikersnaam kennen (MC-09)                      [open]
        AND de code kennen (tweestapsverificatie is verplicht)             [MIT-05, MIT-12]
              OR  de code raden (MC-15)                                    [MIT-06]
              OR  een onderschepte code meteen gebruiken (MC-16)           [open]
              OR  een onderschepte code later gebruiken (MC-16)            [MIT-07]
              OR  het TOTP-geheim buitmaken (MC-17)                        [MIT-17, deels]
                    AND de database lezen                                  [open]
                    AND de gegevenssleutel hebben (MC-22)                  [open]
              OR  de herstelcode gebruiken (MC-19)                         [MIT-11, deels]
  OR  Een nieuw wachtwoord instellen via wachtwoord vergeten (MC-21)       [MIT-14, deels]
        AND gebruikersnaam kennen (MC-09)                                  [open]
        AND de herstelcode hebben (zoals MC-19)                            [MIT-11, deels]
        AND een geldige code uit de app (zoals MC-15 tot MC-17)            [MIT-06, MIT-07, deels]
  OR  De tweede factor zelf instellen (MC-20)                              [open]
        AND het wachtwoord kennen
        AND het account heeft op dat moment geen tweestapsverificatie
  OR  De sessiecookie hebben (MC-04)
        OR  meelezen op het netwerk (geen TLS)                             [open]
        OR  kopieren van een gedeelde browser                              [open, MIT-09 na uitloggen]
        OR  zelf ondertekenen met de sessiesleutel                         [open]
  OR  Via een andere site handelen met de cookie (MC-05)                   [MIT-20]
  OR  Laten klikken in een onzichtbaar frame (MC-24)                       [MIT-21]
  OR  Het wachtwoord zelf wijzigen (MC-12)                                 [MIT-16, deels]
        AND handelen als het slachtoffer (cookie van MC-04, of via MC-05)
        AND het huidige wachtwoord kennen (MC-01, MC-03)
  OR  Via SQL-injectie het wachtwoord laten zien (MC-06)                   [MIT-02]
```

## Doel 3: de dienst onbruikbaar maken

```
Dienst onbruikbaar
  OR  Zeer grote of veel verzoeken sturen (MC-10)
        OR  te lange titel of notitie opslaan                              [MIT-04]
        OR  groot verzoek, dat eerst helemaal wordt ingelezen              [MIT-22]
        OR  veel accounts (elk een Argon2id-hash) of notities aanmaken     [open]
  OR  Alle notities wissen via MC-02                                       [open]
  OR  De database weggooien na overname van de app (MC-08)                 [open]
  OR  De ontwikkelserver van Flask overbelasten (MC-14)                    [MIT-26]
  OR  Een gebruiker buitensluiten met de blokkade (MC-18)                  [open]
```
