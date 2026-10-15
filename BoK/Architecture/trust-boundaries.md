# Trust boundaries

| ID | Tussen | Wat verandert er over deze grens | Sinds |
|----|--------|----------------------------------|-------|
| B-01 | Internet/gebruiker (C-01) en webapplicatie (C-02) | Alles wat van de browser komt is onbetrouwbaar: formuliervelden, cookies, headers, de URL (ook `note_id`). De app moet het zelf valideren. Op de grens staan een lengtegrens op titel en notitie (MIT-04) en een limiet op foute codes in de tweede inlogstap (MIT-06). Geen TLS, geen limiet op inlogpogingen met een wachtwoord of op de grootte van verzoeken, geen CSRF-token. | baseline |
| B-02 | Webapplicatie (C-02) en database (C-03) | De app vertrouwt de database en andersom: de app logt in met de eigenaarrol, dus hij mag alles. Een gecompromitteerde app is een gecompromitteerde database. | baseline |
| B-03 | Database (C-03) en host (C-04) | Wie de host of het volume leest, leest de data. Er is geen versleuteling op schijfniveau of kolomniveau. | baseline |
