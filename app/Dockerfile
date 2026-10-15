FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# BASELINE: de Flask-ontwikkelserver, als root. Geen gunicorn en geen
# aparte gebruiker; dat komt als eigen stap met een eigen entry in de BoK.
CMD ["flask", "--app", "app", "run", "--host", "0.0.0.0", "--port", "5000"]
