# Trust boundaries

| ID | Tussen | Wat verandert er over deze grens | Sinds |
|----|--------|----------------------------------|-------|
| B-01 | Internet/gebruiker (C-01) en webapplicatie (C-02) | Alles wat van de browser komt is onbetrouwbaar: formuliervelden, cookies, headers, de URL (ook `note_id`). De app moet het zelf valideren. Op de grens staan een lengtegrens op titel en notitie (MIT-04), een lengte-eis op nieuwe wachtwoorden (MIT-13), een eigenaarscontrole op elke notitie (MIT-15), het huidige wachtwoord bij wachtwoord wijzigen en account verwijderen (MIT-16) en limieten op foute wachtwoorden (MIT-10), foute codes (MIT-06) en foute herstelcodes (MIT-11, MIT-14). Geen TLS, geen limiet op de grootte van verzoeken of op registreren, geen CSRF-token. | baseline |
| B-02 | Webapplicatie (C-02) en database (C-03) | De app vertrouwt de database en andersom: de app logt in met de eigenaarrol, dus hij mag alles. Een gecompromitteerde app is een gecompromitteerde database. Andersom niet helemaal meer: de sleutel van het TOTP-geheim (A-09) blijft in C-02, dus wie alleen de database heeft, kan het geheim niet lezen (MIT-17). | baseline |
| B-03 | Database (C-03) en host (C-04) | Wie de host of het volume leest, leest de data. Geen versleuteling op schijfniveau; op kolomniveau alleen het TOTP-geheim (MIT-17). | baseline |
