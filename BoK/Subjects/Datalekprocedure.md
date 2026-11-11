# Datalekprocedure

Wat ik doe als er persoonsgegevens kunnen zijn gelekt, en het register waarin elk datalek komt. Hoort bij check 7 van de
AVG-zelfassessment in `Laws.md` ("meld een datalek") en vult het open punt "geen procedure en geen register".

De AVG vraagt drie dingen: een datalek **melden** bij de Autoriteit Persoonsgegevens (AP), waar mogelijk binnen 72 uur
nadat ik er kennis van heb genomen, tenzij het niet waarschijnlijk is dat het een risico oplevert voor de gebruikers
(artikel 33); de **gebruikers zelf informeren** als het risico hoog is (artikel 34); en **elk datalek vastleggen**, ook als ik
het niet meld.

## Wat is een datalek, en wat niet

Een datalek is een inbreuk op de beveiliging waarbij persoonsgegevens per ongeluk of onrechtmatig zijn vernietigd, verloren,
gewijzigd of aan iemand verstrekt of toegankelijk gemaakt die er niets mee te maken heeft.

| Wel een datalek | Geen datalek |
|---|---|
| Iemand heeft de database of een backup gekopieerd | Een blokkade na te veel foute wachtwoorden (MIT-37): de aanval is gestopt |
| Een aanvaller is in het account van een gebruiker gekomen en heeft zijn notities gelezen | Een mislukte login in de log |
| De sleutel voor de versleuteling is uitgelekt (MC-22) en er is ook een kopie van de database | Een aanval die niets opleverde, zoals een geweigerd CSRF-token |
| Een log met gebruikersnamen en IP-adressen is voor iemand anders leesbaar | Een kwetsbaarheid die ik zelf vind en herstel zonder dat iemand erbij kon |
| Notities zijn onleesbaar of weg door een fout, zonder backup die ze terugbrengt | |

Twijfel ik, dan behandel ik het als datalek tot ik het tegendeel weet, en leg ik het vast.

## De drie stappen

### 1. Herkennen

Hoe ik het hoor:

- De alert op een blokkade (MIT-37) en de beveiligingslog in Log Analytics (MIT-31): eerst kijken of er meer is gebeurd dan de
  blokkade zelf, bijvoorbeeld een geslaagde login vlak erna.
- Een melding van een gebruiker, een Blue Teamer of in de hacking week een Red Teamer. Een vondst van een Red Teamer die
  gegevens had kunnen lezen, behandel ik als een datalek.
- Een melding van GitHub, Dependabot of Trivy over een gelekt geheim of een kwetsbaarheid waar iemand bij kon.

De **kennisname** begint op het moment dat ik redelijkerwijs weet dat er mogelijk persoonsgegevens zijn gelekt. Daar tel ik de
72 uur vanaf.

### 2. Beslissen

Binnen een paar uur, en schriftelijk, in het register hieronder:

1. **Zijn er persoonsgegevens bij betrokken?** Gebruikersnamen, IP-adressen en notities zijn dat allemaal (A-11, A-13).
   Zo nee: stop, wel vastleggen.
2. **Is het waarschijnlijk dat het een risico geeft voor de gebruikers?** Kijk wat de aanvaller kon lezen: alleen
   gebruikersnamen is laag; versleutelde notities zonder sleutel is laag; leesbare notities, of de sleutel erbij, is hoog.
   Zo nee: niet melden, wel vastleggen met de reden.
3. **Zo ja:** melden bij de AP via het meldloket datalekken van de AP, binnen 72 uur. Kan het niet binnen 72 uur, dan meld
   ik later en leg ik uit waarom.
4. **Is het risico hoog** (bijvoorbeeld leesbare notities met gevoelige inhoud)? Dan informeer ik ook de gebruikers, in
   gewone taal: wat er gebeurd is, welke gegevens, wat ze moeten doen en wie ze kunnen bereiken. Zonder e-mailadres kan dat
   alleen via de app zelf of de plek waar de app bekendgemaakt is.

In de melding aan de AP: wat er is gebeurd, welke soorten gegevens en ongeveer hoeveel gebruikers, wat de gevolgen kunnen
zijn, en wat ik heb gedaan of ga doen.

### 3. Vastleggen en herstellen

Elk datalek, gemeld of niet, komt in het register. Daarna: het gat dichten (wachtwoorden en sessies ongeldig maken met
`session_version`, sleutels vervangen, de kwetsbaarheid herstellen) en kijken welke maatregel of test (T-) had gefaald.

## Register

Een regel per datalek. Een datalek dat ik niet meld, staat er ook in, met de reden.

| Nr | Ontdekt | Wat is er gebeurd | Welke gegevens, hoeveel gebruikers | Risico en reden | Gemeld bij AP | Gebruikers geïnformeerd | Maatregel |
|---|---|---|---|---|---|---|---|
| | | | | | | | |

Er zijn nog geen datalekken vastgelegd. De hacking week is de eerste echte oefening: elke vondst waarbij gegevens
zichtbaar waren, krijgt een regel.

## Wat er nog mist

- Een afspraak voor als ik zelf niet bereikbaar ben: wie mag in dat geval een melding doen?
- Nooit geoefend: een terugzetting uit de backup (zie `Laws.md`, herstel na een incident). Zonder een geteste backup weet ik niet
  of ik gewiste of onleesbare notities kan terugbrengen.
