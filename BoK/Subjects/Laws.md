# Laws

Drie wetten, en welke er voor deze app geldt:

- **De AVG geldt.** De app verwerkt persoonsgegevens van anderen: gebruikersnamen, IP-adressen in de log, en notities
  waarin van alles kan staan. Ik ben de verwerkingsverantwoordelijke. Hieronder een zelfassessment.
- **NIS2 geldt niet.** Die richtlijn gaat over organisaties in bepaalde sectoren die minstens middelgroot zijn, niet over
  een studentproject. In Nederland is hij uitgewerkt in de Cyberbeveiligingswet.
- **De CRA geldt niet.** Die gaat over producten die in het kader van een handelsactiviteit op de EU-markt komen, betaald
  of gratis; deze app wordt niet verkocht of commercieel aangeboden.

De details per maatregel staan in de entries (MIT- en MC-nummers) en de architectuur (A-, C- en F-nummers).

## AVG

De Algemene verordening gegevensbescherming (Verordening (EU) 2016/679) geldt voor elke verwerking van persoonsgegevens
in de EU, behalve voor puur persoonlijk of huishoudelijk gebruik. Deze app is bedoeld voor anderen, ook in de hacking
week, dus die uitzondering geldt niet.

De beveiligingseisen staan vooral in:

- **Artikel 5, lid 1, onder f:** gegevens worden passend beveiligd, ook tegen ongeoorloofde verwerking, verlies en
  beschadiging (integriteit en vertrouwelijkheid).
- **Artikel 25:** gegevensbescherming door ontwerp en door standaardinstellingen.
- **Artikel 32:** passende technische en organisatorische maatregelen, waaronder versleuteling, de blijvende
  vertrouwelijkheid, integriteit, beschikbaarheid en veerkracht van de systemen, het tijdig herstellen na een incident,
  en het regelmatig testen van de maatregelen.
- **Artikel 33 en 34:** een datalek melden bij de Autoriteit Persoonsgegevens, waar mogelijk binnen 72 uur, tenzij het
  geen risico oplevert; en elk datalek vastleggen.

### Zelfassessment

| Eis | In deze app | Open |
|---|---|---|
| Minimale gegevens (art. 5, lid 1, onder c) | Alleen een gebruikersnaam en een wachtwoordhash; geen e-mailadres. In de log alleen tijd, soort, adres en account, en een naam alleen als het account bestaat (MIT-31) | |
| Bewaartermijn (art. 5, lid 1, onder e) | De log 30 dagen (C-05); een notitie tot de gebruiker hem verwijdert; account verwijderen haalt alles weg (UC-05) | Een verwijderde notitie staat nog tot 7 dagen in de backup van de database |
| Beveiliging (art. 5, lid 1, onder f, en art. 32, lid 1, onder a en b) | Notities en TOTP-geheimen versleuteld, wachtwoorden als Argon2id-hash (MIT-17 tot MIT-19); TLS (MIT-40); 2FA verplicht; de risicomatrix met één hoog restrisico | De draaiende app heeft de sleutel (MC-22) |
| Herstel na een incident (art. 32, lid 1, onder c) | Een backup van 7 dagen; `deployment.py` zet de omgeving opnieuw neer | Nooit een terugzetting getest |
| Regelmatig testen (art. 32, lid 1, onder d) | De tests per misuse case, de regressietest, de scan bij elke pull request, en de hacking week | |
| Privacy by design en by default (art. 25) | Geen e-mailadres gevraagd, geen beheerdersrol die notities kan lezen, alles standaard dicht (MIT-24) | |
| Bijzondere persoonsgegevens (art. 9) | De app vraagt er niet om, maar een notitie is vrije tekst; daarom versleuteld | Of daarom een DPIA nodig is (art. 35), is niet beoordeeld |
| Rechten van de gebruiker (art. 15 en 17) | Inzage: de gebruiker ziet zijn profiel en notities (UC-06). Verwijderen: het account en alle notities (UC-05) | Geen export van de eigen notities (art. 20) |
| Informatie (art. 13) | | Geen privacyverklaring: doel, grondslag en bewaartermijn staan nergens voor de gebruiker |
| Datalekken (art. 33) | Een aanval laat een spoor na (MIT-31), en een blokkade geeft een mail (MIT-37) | Geen procedure om binnen 72 uur te melden, en geen register van datalekken |
| Waar de gegevens staan | Op Azure in France Central, in de EU | Microsoft is verwerker; de verwerkersvoorwaarden heb ik niet nagekeken |

**Conclusie:** de technische kant staat; wat ontbreekt, is organisatorisch: een privacyverklaring met doel, grondslag en
bewaartermijn, een afweging of een DPIA nodig is, en een procedure en register voor datalekken.

## NIS2

De NIS2-richtlijn (Richtlijn (EU) 2022/2555) geldt voor publieke en private organisaties in de sectoren van bijlage I en
II die minstens middelgroot zijn volgens Aanbeveling 2003/361/EG, en voor enkele soorten ongeacht hun omvang (artikel
2). Die organisaties moeten risicobeheersmaatregelen nemen (artikel 21) en een significant incident in stappen melden
(artikel 23). In Nederland staat dit in de Cyberbeveiligingswet (Stb. 2026, 187), in werking sinds 15 augustus 2026.

Voor deze app geldt NIS2 niet: er is geen organisatie, en een studentproject is niet middelgroot. Wel lijken de
maatregelen van artikel 21, lid 2, op de BoK: risicoanalyse, incidentafhandeling, continuïteit en backups, beveiliging van de
toeleveringsketen, veilige ontwikkeling met het afhandelen van kwetsbaarheden, cryptografie, toegangsbeheer en
meervoudige authenticatie. Die zijn hier gebouwd omdat ze bij een veilige app horen, niet omdat de wet het vraagt.

## CRA

De Cyber Resilience Act (Verordening (EU) 2024/2847) stelt eisen aan producten met digitale elementen, hardware en
software, die op de EU-markt worden aangeboden: verspreid of gebruikt in het kader van een handelsactiviteit, betaald of
gratis. Hij is in werking sinds 10 december 2024; de meldplicht voor actief
misbruikte kwetsbaarheden geldt vanaf 11 september 2026, de rest vanaf 11 december 2027. Opensourcesoftware die niet in het kader van een
handelsactiviteit wordt aangeboden, valt erbuiten; donaties zonder winstoogmerk maken een project niet commercieel.

Voor deze app geldt de CRA niet: hij wordt niet verkocht of commercieel aangeboden. Zou dat wel gebeuren, dan zijn de
eisen voor het afhandelen van kwetsbaarheden (bijlage I, deel II) het eerst van belang; wat de app daarvan al doet, staat
in `Standards.md` onder EN 40000: de SBoM en de updates wel, een meldbeleid en het openbaar maken van opgeloste
kwetsbaarheden nog niet.

## Bronnen

Opgehaald en gecontroleerd op 19-10-2026.

- AVG, artikel 32 en 33 (tekst via gdpr-info.eu, dat de tekst uit het Publicatieblad overneemt): https://gdpr-info.eu/art-32-gdpr/ en https://gdpr-info.eu/art-33-gdpr/
- Europese Commissie, Cyber Resilience Act (in werking 10-12-2024, meldplicht vanaf 11-09-2026, de rest vanaf 11-12-2027), bijgewerkt op 07-09-2026: https://digital-strategy.ec.europa.eu/en/policies/cyber-resilience-act
- NIS2, artikel 2 en artikel 21 (tekst via Springlex, uit OJ L 333 van 27-12-2022): https://www.springlex.eu/en/packages/nis2/nis2-directive/article-2/ en https://www.springlex.eu/en/packages/nis2/nis2-directive/article-21/
- NJB, Cyberbeveiligingswet (wet van 08-07-2026, Stb. 2026, 187 en 189; in werking op 15-08-2026): https://www.njb.nl/wetgeving/staatsbladen/cyberbeveiligingswet/
- Felix Reda (GitHub), 10-12-2024, bijgewerkt 17-12-2024: wat de CRA betekent voor ontwikkelaars ("in the course of a commercial activity, whether in return for payment or free of charge"): https://github.blog/open-source/maintainers/what-the-eus-new-software-legislation-means-for-developers
