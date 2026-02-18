# JSON Schema Utils Compiler

```docker
# dev version install, which requires strange dependencies because of re2, despite existing packages
RUN apk update && apk upgrade && apk add curl git re2 re2-dev py3-pybind11 py3-pybind11-dev py3-re2 g++ && apk cache clean
RUN pip install git+https://github.com/clairey-zx81/json-model@dev
RUN pip install git+https://github.com/zx80/json-schema-utils@dev
```

```sh
docker build --no-cache -t docker.io/zx80/python-jsu -f Dockerfile.dev .
docker image ls zx80/python-jsu
docker run --rm --entrypoint /bin/sh -it zx80/python-jsu
bowtie smoke -i docker.io/zx80/python-jsu

for version in 7 6 4 3 2019 2020 ; do
  echo "# version $version"
  bowtie suite -i docker.io/zx80/python-jsu $version > suite_$version.jsonl
  bowtie summary -s failures suite_$version.jsonl
done
```
