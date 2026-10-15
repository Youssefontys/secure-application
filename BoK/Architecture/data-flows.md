# Datastromen

| ID | Van | Naar | Data | Protocol | Trust boundary | Sinds |
|----|-----|------|------|----------|----------------|-------|
| F-01 | C-01 Browser | C-02 Webapplicatie | Formulieren: gebruikersnaam en wachtwoord (A-01, A-04), notities (A-02), sessiecookie (A-03) | HTTP, zonder TLS | B-01 | baseline |
| F-02 | C-02 Webapplicatie | C-01 Browser | HTML-pagina's met notities (A-02) en de gebruikersnaam in de begroeting (A-04), statische bestanden, `Set-Cookie` met sessiecookie (A-03) | HTTP, zonder TLS | B-01 | baseline |
| F-03 | C-02 Webapplicatie | C-03 Database | SQL met parameters: wachtwoord leesbaar (A-01), notities leesbaar (A-02), gebruikersnamen | PostgreSQL-protocol op het Docker-netwerk, zonder TLS, ingelogd als de eigenaarrol | B-02 | baseline |
| F-04 | C-03 Database | C-04 Databasevolume | Alle databasebestanden, leesbaar | Bestandssysteem | B-03 | baseline |
