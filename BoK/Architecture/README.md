# Architecture

Hier staat alles wat in de totale architectuur zit, zodat er achteraf een
diagram van gemaakt kan worden. We schrijven op wat er is gebouwd, niet wat
er ooit zou kunnen komen. Elk onderdeel krijgt een vast ID, zodat de Threat
Analysis ernaar kan verwijzen en een diagram dezelfde namen gebruikt.

## Bestanden

- `components.md`: alle onderdelen (app, database, ...), met type en wat ze doen.
- `data-flows.md`: wie praat met wie, welke data, over welk protocol.
- `trust-boundaries.md`: de grenzen tussen vertrouwde en niet-vertrouwde zones.

## Regels

- ID's: `C-` onderdeel, `F-` datastroom, `B-` trust boundary, `A-` asset (data
  die beschermd moet worden). Een ID verandert nooit en wordt nooit hergebruikt.
- Een datastroom noemt altijd: van, naar, data, protocol, en over welke
  trust boundary hij gaat. Daar zitten de meeste dreigingen.
- Elke wijziging in de architectuur is een eigen commit, zodat de geschiedenis
  laat zien wanneer een onderdeel erbij kwam.
