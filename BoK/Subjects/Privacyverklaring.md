# Privacyverklaring

De tekst die een gebruiker bij het registreren leest, met het vinkje waarmee hij toestemming geeft. Hij hoort bij check 5 van de
AVG-zelfassessment in `Laws.md` (Ondernemersplein: "vertel uw klanten in een privacyverklaring wat u met hun
persoonsgegevens doet"). De app laat hem nog niet zien: dat is een open punt. Wat tussen `[ ]` staat, vul ik in voordat hij live gaat.

Dit is de Nederlandse bron. De app zelf is Engels: de Engelse tekst staat in `app/web/templates/privacy.html` (pagina
`/privacy`), het vinkje op de registratiepagina in `app/web/templates/auth.html`.

De tekst is geschreven voor de gebruiker, dus in de je-vorm en zo kort mogelijk. Alles wat erin staat, komt uit de code, de
Terraform-bestanden of de entries; de verwijzingen eronder zeggen waar.

---

## Privacyverklaring Notities

**Wie ben ik?** Ik ben youssefontys, student, en ik bouw deze app voor een opdracht. Ik ben verantwoordelijk voor de gegevens die
je hier invult. Vragen of verzoeken: this@maildoestnotexit.com.

**Welke gegevens bewaar ik?**

- Je gebruikersnaam, en je wachtwoord als hash: het wachtwoord zelf staat nergens.
- Als je tweestapsverificatie aanzet: het geheim van je authenticator-app (versleuteld) en een hash van je herstelcode.
- Je notities: titel en tekst, versleuteld, met het moment van aanmaken en wijzigen.
- Een beveiligingslog: tijd, soort gebeurtenis (bijvoorbeeld "inloggen mislukt"), je IP-adres en, als je account bestaat, je
  gebruikersnaam. Wachtwoorden en codes staan er nooit in.
- Een sessiecookie om je ingelogd te houden, maximaal 8 uur. Ik gebruik geen andere cookies en geen tracking.

Ik vraag geen e-mailadres, naam of telefoonnummer. In je notities kun je zelf alles typen. Zet er liever geen gevoelige
gegevens in, zoals over je gezondheid: dit is een testomgeving.

**Waarom, en op welke grond?**

- Je account en je notities bewaar ik om de app te laten werken, op grond van **jouw toestemming**: het vinkje bij het
  registreren. Je kunt die toestemming altijd intrekken door je account te verwijderen.
- De beveiligingslog bewaar ik om aanvallen te zien en te stoppen, op grond van **gerechtvaardigd belang**. Dat belang gaat
  voor omdat de log anders niets waard is, en daarom hangt hij niet af van je toestemming.
- Ik gebruik je gegevens alleen hiervoor. Geen marketing, en ik deel ze met niemand anders dan hieronder staat.

**Hoelang?**

| Gegeven | Hoelang |
|---|---|
| Account en notities | Tot je ze zelf verwijdert |
| Een verwijderd account of een verwijderde notitie | Binnen 7 dagen ook uit de backup weg |
| Beveiligingslog | 30 dagen |

**Waar, en wie heeft het?**

- Op Microsoft Azure in France Central, in de Europese Unie. Microsoft verwerkt de gegevens in mijn opdracht (verwerker).
- Niemand anders krijgt je gegevens. De code staat openbaar op GitHub, maar zonder gegevens van gebruikers.
- Bij een blokkade (te veel mislukte pogingen) krijgt een beheerder een melding per mail.

**De hacking week.** In de hacking week wordt de app met toestemming aangevallen door medestudenten. Daardoor kunnen gegevens in
de omgeving in handen komen van mensen die ze normaal niet zien. Gebruik in die week dus geen echte gegevens.

**Wat zijn je rechten?** Je kunt je profiel en notities inzien, notities aanpassen, en je account met alle notities
verwijderen. Een export van je notities heeft de app nog niet; vraag er naar via this@maildoestnotexit.com als je ze wilt hebben. Een
verzoek beantwoord ik binnen een maand.

**Klacht?** Kom je er met mij niet uit, dan kun je een klacht indienen bij de Autoriteit Persoonsgegevens
(autoriteitpersoonsgegevens.nl).

---

## De tekst bij het vinkje

> Ik heb de privacyverklaring gelezen. Ik geef toestemming om mijn gebruikersnaam en notities te bewaren, versleuteld, zolang
> mijn account bestaat. Ik kan mijn account en notities altijd zelf verwijderen.

Een paar eisen aan het vinkje, naar de AVG en de AP: het staat **niet vooraf aangevinkt**, het zit **niet verstopt** in andere
voorwaarden, en intrekken is even makkelijk als geven (account verwijderen, UC-05). Zonder vinkje geen account.

## Waar het uit komt

| Zin in de verklaring | Bron |
|---|---|
| Gebruikersnaam, wachtwoordhash, TOTP-geheim, herstelcode | `db/schema.sql` (tabel `users`); MIT-17 tot MIT-19 |
| Notities versleuteld | `db/schema.sql` (tabel `notes`); MIT-18 |
| Het log en wat erin staat | MIT-31, `app/events.py`; A-11 |
| Sessiecookie van 8 uur | `app/app.py` (`PERMANENT_SESSION_LIFETIME`) |
| Log 30 dagen | `terraform/logs.tf` (`retention_in_days`); C-05 |
| Backup 7 dagen | `terraform/database.tf` (`backup_retention_days`) |
| Azure, France Central, Microsoft als verwerker | `Laws.md`, zelfassessment |
| Mail bij een blokkade | MIT-37 |
| Account en notities verwijderen, profiel inzien | UC-05, UC-06 |
