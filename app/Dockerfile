FROM python:3.15-slim

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
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
