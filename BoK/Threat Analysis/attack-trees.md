# Attack trees

Per aanvallersdoel een boom, afgeleid uit de misuse cases in `entries.md`.
`OR` = een van de takken is genoeg. `AND` = alle takken zijn nodig.
`[MIT-xx]` = deze tak is tegengehouden. `[open]` = nog geen maatregel.

## Doel 1: notities van een andere gebruiker lezen of vernietigen

```
Notities van een ander lezen of wijzigen
  OR  Via een eigen account andermans notitie-id invullen (MC-02)        [open]
        AND eigen account aanmaken en inloggen
        AND notitie-id raden (opeenvolgende getallen)
  OR  De database direct lezen (MC-01, MC-08)                             [open]
        OR  rechtstreekse query met de eigenaarrol
        OR  het volume of een backup lezen
        OR  de app overnemen via een afhankelijkheid (MC-11)
              OR  bekende kwetsbaarheid, niet bijgewerkt                   [open]
              OR  kwaadaardige nieuwe pakketversie                         [MIT-03]
              OR  kwetsbaarheid of andere image achter de tag              [open]
  OR  Script in een notitie laten uitvoeren (MC-07)                       [MIT-01]
  OR  Als de gebruiker handelen (zie doel 2)
```

## Doel 2: als een andere gebruiker handelen (account overnemen)

```
Account overnemen
  OR  Het wachtwoord kennen
        OR  uit de database lezen (MC-01)                                  [open]
        OR  raden of stuffing (MC-03)                                      [open]
              AND gebruikersnaam kennen (MC-09)                            [open]
  OR  De sessiecookie hebben (MC-04)
        OR  meelezen op het netwerk (geen TLS)                             [open]
        OR  kopieren van een gedeelde browser                              [open]
        OR  zelf ondertekenen met de sessiesleutel                         [open]
  OR  Via een andere site handelen met de cookie van het slachtoffer (MC-05) [open]
  OR  Via SQL-injectie het wachtwoord laten zien (MC-06)                   [MIT-02]
```

## Doel 3: de dienst onbruikbaar maken

```
Dienst onbruikbaar
  OR  Zeer grote of veel verzoeken sturen (MC-10)                          [open]
  OR  Alle notities wissen via MC-02                                       [open]
  OR  De database weggooien na overname van de app (MC-08)                 [open]
```
