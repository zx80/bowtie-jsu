FROM python:3.14.0-alpine
WORKDIR /usr/src/myapp
ARG IMPLEMENTATION_VERSION
RUN python -m pip install --no-cache-dir json-schema-utils${IMPLEMENTATION_VERSION:+==${IMPLEMENTATION_VERSION}}[compile]
COPY bowtie_jsu_python.py .
CMD ["python3", "bowtie_jsu_python.py"]
