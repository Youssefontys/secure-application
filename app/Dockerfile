# Vast op versie en digest (MIT-03): een tag als 3.15-slim schuift mee met elke nieuwe build van de image.
FROM python:3.15.0-slim-trixie@sha256:2da676046630d7bf14c6764ae1143dc7fa0377a53f94bf5a642f0b214aca5bce

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
# Daarna pip zelf weg: de app en de schema-job gebruiken hem niet, en pip neemt eigen kopieën van
# urllib3, msgpack en setuptools mee waarin Trivy bekende lekken vond (MC-11).
RUN pip install --no-cache-dir -r requirements.txt \
 && pip uninstall --yes pip

COPY . .

# Een gewone gebruiker zonder shell en zonder schrijfrecht op de code: wie de app
# overneemt, is geen root en kan de code niet aanpassen (MC-14).
# Daarna van elk programma de setuid- en setgid-bit weg, zodat ook mount, su en passwd met de rechten
# van die gebruiker draaien en niet als root (MIT-42); de VEX-verklaringen voor mount steunen hierop.
RUN useradd --system --no-create-home --shell /usr/sbin/nologin app \
 && find / -xdev -type f -perm /6000 -exec chmod a-s {} +
USER app

EXPOSE 5000

# Gunicorn in plaats van de ontwikkelserver van Flask, die zelf zegt niet voor
# productie te zijn (MC-14). Twee workers passen bij 0,25 vCPU op Container Apps.
# Zonder besturingssocket: die gebruiken we niet, en app heeft bewust geen homemap.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--no-control-socket", "app:app"]
