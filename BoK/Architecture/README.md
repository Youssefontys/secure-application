# Architecture

Hier staat alles wat in de totale architectuur zit, zodat er achteraf een
diagram van gemaakt kan worden. We schrijven op wat er is gebouwd, niet wat
er ooit zou kunnen komen. Elk onderdeel krijgt een vast ID, zodat de Threat
Analysis ernaar kan verwijzen en een diagram dezelfde namen gebruikt.

## Bestanden

- `components.md`: alle onderdelen en de data (assets) die ze bewaren.
- `data-flows.md`: wie praat met wie, welke data, over welk protocol.
- `trust-boundaries.md`: de grenzen tussen vertrouwde en niet-vertrouwde zones.
- `auth-points.md`: elk punt waar iets wordt vastgesteld (authenticatie) of
  toegestaan (autorisatie), en wat daar ontbreekt.

## Regels

- Voorvoegsels: `C-` onderdeel, `F-` datastroom, `B-` trust boundary, `A-` asset
  (data die beschermd moet worden), `AU-` authenticatiepunt, `AZ-` autorisatiepunt.
  Een ID verandert nooit en wordt nooit hergebruikt.
- Een datastroom noemt altijd: van, naar, data, protocol, en over welke
  trust boundary hij gaat. Daar zitten de meeste dreigingen.
- Een authenticatie- of autorisatiepunt noemt het onderdeel, de datastroom
  waarop het zit, wat er wordt gecontroleerd en hoe. Staat er geen controle,
  dan staat dat er ook (kolom Status), want juist dat is het open risico.
- Elke wijziging in de architectuur is een eigen commit, zodat de geschiedenis
  laat zien wanneer een onderdeel erbij kwam.
