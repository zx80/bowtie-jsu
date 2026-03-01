FROM alpine:3.23

# NOTE python images do not seem to have google-re2 python wrapper available
# without recompiling from sources, whereas the base alpine image has it,
# so start from alpine.

RUN mkdir /app /app/schema-cache-by-hashed-urls
WORKDIR /app

# allow to install from package (not set) or build from sources (branch or commit)
ARG JMC
ARG JSU

# system site package dependencies
RUN apk add git py3-pip py3-re2 icu-data-full

# setup Python virtual environment
ENV PATH=/venv/bin:$PATH
RUN python -m venv /venv --system-site-packages
RUN pip install jsonschema-specifications

RUN if [ "$JMC" ] ; then jmc="git+https://github.com/clairey-zx81/json-model@$JMC" ; fi ; \
    pip install "${jmc:-json_model_compiler}"

RUN if [ "$JSU" ] ; then jsu="git+https://github.com/zx80/json-schema-utils@$JSU" ; fi ; \
    pip install "${jsu:-json_schema_utils}"

# harness script
COPY bowtie_jsu_python.py .
CMD ["python3", "./bowtie_jsu_python.py"]
