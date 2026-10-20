# Pinned on version and digest (MIT-03): a tag like 3.15-slim moves along with every new build of the image.
FROM python:3.15.0-slim-trixie@sha256:2da676046630d7bf14c6764ae1143dc7fa0377a53f94bf5a642f0b214aca5bce

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# The libpq of Debian, pinned on version (MIT-03): psycopg loads it, Debian updates it and the scan sees it, with what
# it pulls in (MIT-43). When a newer version comes out, this one disappears from Debian and the build fails: update it then.
RUN apt-get update \
 && apt-get install --yes --no-install-recommends libpq5=17.11-0+deb13u1 \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Then remove pip itself: the app and the schema job do not use it, and pip brings its own copies of
# urllib3, msgpack and setuptools, in which Trivy found known vulnerabilities (MC-11).
RUN pip install --no-cache-dir -r requirements.txt \
 && pip uninstall --yes pip

COPY . .

# An ordinary user without a shell and without write access to the code: whoever takes over
# the app is not root and cannot change the code (MC-14).
# Then remove the setuid and setgid bit from every program, so mount, su and passwd also run with the rights
# of that user and not as root (MIT-42); the VEX statements for mount rely on this.
RUN useradd --system --no-create-home --shell /usr/sbin/nologin app \
 && find / -xdev -type f -perm /6000 -exec chmod a-s {} +
USER app

EXPOSE 5000

# Gunicorn instead of the development server of Flask, which itself says it is not for
# production (MC-14). Two workers fit 0.25 vCPU on Container Apps.
# Without a control socket: we do not use it, and app deliberately has no home directory.
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--no-control-socket", "app:app"]
