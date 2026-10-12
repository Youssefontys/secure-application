# Threat Analysis

We werken achterwaarts: we bouwen eerst, en schrijven de use case, misuse case
en mitigation op op het moment dat ze ontstaan. Er staat dus niets in wat niet
in de code of de architectuur voorkomt.

Elke entry is zo geschreven dat er een attack tree van gemaakt kan worden:
een doel van de aanvaller bovenin, daaronder de manieren om dat te bereiken
(OR) en de stappen die er allemaal voor nodig zijn (AND).

## Bestanden

- `entries.md`: één entry per use case / misuse case / mitigation, nieuwste onderaan.
- `attack-trees.md`: per aanvallersdoel de boom, opgebouwd uit de entries.

## Hoe een entry werkt

- ID's: `UC-` use case, `MC-` misuse case, `MIT-` mitigation. Nooit hergebruiken.
- Een misuse case noemt het **aanvallersdoel** (de wortel van een boom), de
  **aanvaller**, de getroffen **assets** (`A-`) en **onderdelen** (`C-`), en de
  **stappen**. Per stap staat of hij een OR of AND is ten opzichte van zijn broers.
- Een mitigation verwijst naar de misuse case(s) en de stap(pen) die hij
  tegenhoudt, en naar de plek in de code. Een stap zonder mitigation blijft
  zichtbaar als open risico.
- Status: `open`, `gebouwd`, `bewezen` (er is een test of bewijs).

## Sjabloon

```
### MC-000 Korte naam
- Aanvallersdoel:
- Aanvaller:
- Assets / onderdelen: A-?, C-?
- Gerelateerde use case: UC-?
- Stappen:
  - OR  1. ...
  - OR  2. ...
    - AND 2a. ...
    - AND 2b. ...
- Mitigaties: MIT-? (stap 1), nog geen (stap 2)
- Restrisico:
- Sinds (commit):
```
