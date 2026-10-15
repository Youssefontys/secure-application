FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

# De ontwikkelserver van Flask, als root. Werkt, maar is niet voor productie
# gemaakt, en wie de app overneemt heeft meteen rootrechten in de container.
CMD ["flask", "--app", "app", "run", "--host", "0.0.0.0", "--port", "5000"]
