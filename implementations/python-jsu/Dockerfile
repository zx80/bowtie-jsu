FROM alpine:3.23
RUN mkdir /app
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
    apk del git && \
    apk cache clean
# no: rm -rf /root/.cache

# cache meta schemas
RUN apk add curl openssl && \
    for url in \
        "http://json-schema.org/draft-03/schema" \
        "http://json-schema.org/draft-04/schema" \
        "http://json-schema.org/draft-06/schema" \
        "http://json-schema.org/draft-07/schema" \
        "https://json-schema.org/draft/2019-09/schema" \
        "https://json-schema.org/draft/2019-09/meta/core" \
        "https://json-schema.org/draft/2019-09/meta/format" \
        "https://json-schema.org/draft/2019-09/meta/applicator" \
        "https://json-schema.org/draft/2019-09/meta/validation" \
        "https://json-schema.org/draft/2019-09/meta/content" \
        "https://json-schema.org/draft/2019-09/meta/meta-data" \
        "https://json-schema.org/draft/2020-12/schema" \
        "https://json-schema.org/draft/2020-12/meta/core" \
        "https://json-schema.org/draft/2020-12/meta/format-annotation" \
        "https://json-schema.org/draft/2020-12/meta/applicator" \
        "https://json-schema.org/draft/2020-12/meta/validation" \
        "https://json-schema.org/draft/2020-12/meta/content" \
        "https://json-schema.org/draft/2020-12/meta/meta-data" \
        "https://json-schema.org/draft/2020-12/meta/unevaluated" ; \
    do \
      uh=$(echo -n $url | openssl sha3-256 | cut -d' ' -f 2| cut -c 1-16 ) ; \
      curl -sL "$url" > "./$uh.json" ; \
    done && \
    apk del curl openssl && \
    apk cache clean

COPY bowtie_jsu_python.py .
CMD ["python3", "./bowtie_jsu_python.py"]
