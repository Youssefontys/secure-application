# Triage van meldingen, en de VEX

Elke melding van HIGH of CRITICAL houdt de check tegen, ook als er nog geen oplossing is. Hij gaat pas door als er een
beslissing is: bijwerken, weghalen, afschermen, of een verklaring in `openvex.json` dat de image niet geraakt wordt,
met de reden erbij (MIT-41). Zo'n verklaring geldt voor één versie van een pakket. Komt er een nieuwe versie, dan komt
de melding terug, en beslis je opnieuw.

Dit is het product van deelvraag 2 van het onderzoek (SBoM in CI/CD): "Hoe kunnen kwetsbare componenten uit een
SBoM-scan worden getrieerd?"

## Waarom

Tot deze stap hield de scan alleen een lek mét oplossing tegen (`--ignore-unfixed`). Dat is ook een beslissing: alle
lekken zonder oplossing accepteren, zonder ernaar te kijken. Op de image van `main` (368a30d) waren dat er 164, waarvan
44 HIGH (T-114). Wat die meldingen waard zijn, bleek pas bij het nakijken:

- **44 meldingen waren 8 lekken.** Eén lek in util-linux staat bij elk van de 9 pakketten die uit util-linux komen.
- **Geen enkele staat in CISA KEV** (de lijst van lekken die echt misbruikt worden), en de hoogste EPSS-score van de 8
  is 0,005: een kans van een half procent op misbruik in de komende 30 dagen, ergens ter wereld.
- **Ernst en EPSS wijzen elk een andere kant op.** De hoogste EPSS-scores (tot 0,058) horen bij oude glibc-lekken van
  ernst LOW, die de scan niet eens meetelt.
- **Bij 5 van de 8 zit de lekke code niet in de image, of draait hij nooit.** Bij de andere 3, alle drie in mount,
  houdt een maatregel het tegen: een lege `/etc/fstab`, en sinds deze stap geen setuid-bit meer op mount (MIT-42).

Ernst alleen zegt dus weinig over deze image. Wat telt, is of de lekke code er is, of hij draait, en of een aanvaller
erbij kan.

## De flow

Per lek, niet per melding: eerst de meldingen van hetzelfde lek samennemen.

1. **Is er een oplossing?** Bijwerken: Dependabot stelt een nieuwe versie of digest voor (MIT-33), of zet de digest van
   de base-image zelf bij. Klaar.
2. **Is het onderdeel nodig?** Nee: weghalen uit de image. Zo ging pip weg (b31d334), met zijn vier lekken (T-105).
   Weghalen is beter dan een verklaring: een onderdeel dat er niet is, geeft ook geen nieuwe meldingen.
3. **Staat het lek in CISA KEV, of is de EPSS-score 0,1 of hoger?** Dan eerst dit lek, dezelfde dag: weghalen of
   afschermen. Een verklaring alleen is dan niet genoeg. De grens van 0,1 is een eigen keuze; op 19-10-2026 kwam geen
   enkele melding in de buurt.
4. **Zit de lekke code in de image?** Kijk welk bestand of programma het lek heeft, en of het pakket dat bevat
   (`dpkg -L <pakket>` in de container). Nee: `not_affected`, met `vulnerable_code_not_present`.
5. **Draait de lekke code?** Kijk welke bibliotheken de processen van de app laden (`/proc/<pid>/maps`), en of de app
   het programma ooit start. Nee: `not_affected`, met `vulnerable_code_not_in_execute_path`.
6. **Kan een aanvaller er toch bij, maar houdt iets het tegen?** Bijvoorbeeld: mount zonder setuid-bit, en een lege
   `/etc/fstab`. Leg de maatregel vast in de Dockerfile, en dan `not_affected` met
   `inline_mitigations_already_exist`.
7. **Anders is de image geraakt.** Zet `affected` met een `action_statement`: wat je gaat doen, en wanneer. De check
   blijft dan falen. Moet er toch iets door, dan alleen tijdelijk: een regel met `expired_at` in een ignore-bestand van
   Trivy. Dat werkt (T-115), maar is nog niet nodig geweest, dus staat het niet in de workflow.

Een melding van MEDIUM of LOW houdt de check niet tegen. Stap 3 geldt daar wel: een lek in KEV, of met een hoge
EPSS-score, krijgt voorrang, wat de ernst ook is. Dat kijk je met de hand na op de bewaarde SBoM, zoals in T-114;
automatisch gebeurt het nog niet.

## Regels voor `openvex.json`

- **OpenVEX 0.2.0, met een PURL per pakket.** Een CycloneDX-VEX wijst via het `serialNumber` naar één SBoM. Trivy geeft
  elke SBoM een nieuw nummer, ook bij dezelfde image (T-114), dus zo'n VEX zou bij elke build opnieuw moeten. Een
  PURL blijft hetzelfde zolang het pakket hetzelfde is.
- **Altijd met versie, zonder qualifiers.** Zonder versie geldt de verklaring voor elke versie, ook een die je nooit
  bekeken hebt (T-115). Met de qualifier `distro` valt hij weg bij elke nieuwe Debian-versie.
- **Altijd een reden:** bij `not_affected` een `justification` en een `impact_statement`, bij `affected` een
  `action_statement`. Trivy filtert ook een `not_affected` zonder reden weg (T-115). Daarom controleert de stap VEX
  controleren in `image.yml` dat eerst, en faalt hij anders.
- **Geen `fixed`.** Trivy filtert ook die weg, maar of een lek is opgelost, zie je aan de versie; dat hoort de scan
  zelf te zien.
- **Alleen via een pull request,** zoals elke wijziging op `main`. Verhoog `version` bij elke wijziging, en zet
  `last_updated`.

## Wat het niet oplost

- **Een verklaring kan fout zijn.** De check ziet of er een reden staat, niet of hij klopt. Dat ziet alleen wie de
  pull request mergt (MC-30, stap 6).
- **Het werk.** Elk nieuw lek van HIGH of CRITICAL in Debian, ook zonder oplossing, houdt elke pull request tegen tot
  er een beslissing is, ook een pull request die alleen de BoK verandert.
- **Een lek dat na de build bekend wordt,** ziet de scan pas bij de volgende pull request of push.
- **De VEX is openbaar.** Hij vertelt welke lekken er in de image zitten, en waarom wij denken dat ze niet bereikbaar
  zijn. Dat staat ook in de SBoM; de code en de image zijn al openbaar.

## Bronnen

Opgehaald op 19-10-2026.

- OpenVEX, specificatie v0.2.0 (statussen en justifications): https://github.com/openvex/spec/blob/main/OPENVEX-SPEC.md
- Trivy, VEX als bestand (CycloneDX via BOM-Link met `serialNumber`, OpenVEX via PURL; "EXPERIMENTAL"): https://trivy.dev/latest/docs/supply-chain/vex/file/
- CISA, Known Exploited Vulnerabilities (catalogus 2026.10.16, 1748 lekken): https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json
- FIRST, EPSS API (scores van 19-10-2026): https://api.first.org/data/v1/epss
