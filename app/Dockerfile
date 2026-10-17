# Vast op versie en digest (MIT-03): een tag als 3.15-slim schuift mee met elke nieuwe build van de image.
FROM python:3.15.0-slim-trixie@sha256:2da676046630d7bf14c6764ae1143dc7fa0377a53f94bf5a642f0b214aca5bce

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Een gewone gebruiker zonder shell en zonder schrijfrecht op de code: wie de app
# overneemt, is geen root en kan de code niet aanpassen (MC-14).
RUN useradd --system --no-create-home --shell /usr/sbin/nologin app
USER app

EXPOSE 5000

# Gunicorn in plaats van de ontwikkelserver van Flask, die zelf zegt niet voor
# productie te zijn (MC-14). Twee workers passen bij 0,25 vCPU op Container Apps.
# Zonder besturingssocket: die gebruiken we niet, en app heeft bewust geen homemap.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--no-control-socket", "app:app"]
