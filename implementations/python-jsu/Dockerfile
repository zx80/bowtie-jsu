FROM alpine:3.23

# NOTE python images do not seem to have google-re2 python wrapper available
# without recompiling from sources, whereas the base alpine image has it,
# so start from alpine.

RUN mkdir /app /app/schema-cache-by-hashed-urls
WORKDIR /app

# allow to install from package (not set) or build from sources (branch or commit)
ARG JMC
ARG JSU

# setup virtual environment
ENV PATH=/venv/bin:$PATH
RUN if [ "$JMC" ] ; then \
        jmc="git+https://github.com/clairey-zx81/json-model@$JMC" ; \
    else \
        jmc=json_model_compiler ; \
    fi && \
    if [ "$JSU" ] ; then \
        jsu="git+https://github.com/zx80/json-schema-utils@$JSU" ; \
    else \
        jsu=json_schema_utils ; \
    fi && \
    apk add git py3-pip py3-re2 icu-data-full && \
    python -m venv /venv --system-site-packages && \
    pip install "$jmc" && \
    pip install "$jsu" && \
    pip install jsonschema-specifications && \
    apk del git && \
    apk cache clean
# no: rm -rf /root/.cache

COPY bowtie_jsu_python.py .
CMD ["python3", "./bowtie_jsu_python.py"]
