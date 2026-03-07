#! /usr/bin/env python3

"""
A Bowtie generic harness for the json-schema-utils schema validator
using JSON Model Compiler as a backend for various languages.
"""

from pathlib import Path
import hashlib
import json
import platform
import shutil
import subprocess
import sys
import traceback

from jsonschema_specifications import REGISTRY

type JsonObject = dict[str, Json]
type JsonArray = list[Json]
type Json = None | bool | int | float | str | JsonArray | JsonObject

# available JSON Schema specifications
SPECS: dict[str, JsonObject] = {
    url: REGISTRY.contents(url) for url in REGISTRY
}

# JSON Schema version URL to internal version
VERSIONS: dict[str, int] = {
    "https://json-schema.org/draft/2020-12/schema": 9,
    "https://json-schema.org/draft/2019-09/schema": 8,
    "http://json-schema.org/draft-07/schema#": 7,
    "http://json-schema.org/draft-06/schema#": 6,
    "http://json-schema.org/draft-04/schema#": 4,
    "http://json-schema.org/draft-03/schema#": 3,
}

# cache is used for registry and meta schemas
CACHE: Path = Path(__file__).parent / "schema-cache-by-hashed-urls"

# directory for temporary files
TMP: Path = Path(__file__).parent / "work"

def get_version(cmd: list[str]) -> str:
    """Run external command and return first non empty output line."""
    ps = subprocess.run(cmd, text=True, capture_output=True, check=True)  # noqa: S603
    lines = list(filter(lambda s: s != "", ps.stdout.split("\n")))
    return lines[0]

def tmp_json_file(filename: str, data: Json) -> Path:
    """Put JSON data into a temporary file."""
    file: Path = TMP / filename
    with Path.open(file, "w") as sf:
        json.dump(data, sf)
    return file


class RunnerError(Exception):
    pass


class Runner:

    def __init__(self, language: str = "python"):

        # setup language
        self.language: str = language

        # current dialect
        self.version: int | None = None

        # count input lines for some error messages
        self.line: int = 0

        # per-language settings:
        # - output: compiler output file
        # - runner: how to run the generated file
        # - vers_cmd: command to get language version
        match language:
            case "python":
                self.output = "schema.py"
                self.runner = ["python"]
                vers_cmd = ["python", "--version"]
            case "c":
                self.output = "schema.out"
                self.runner = []
                vers_cmd = ["cc", "--version"]
            case "js":
                self.output = "schema.js"
                self.runner = []
                vers_cmd = ["node", "--version"]
            case "java":
                self.output = "schema.class"
                self.runner = ["java"]
                vers_cmd = ["java", "--version"]
            case "perl":
                self.output = "schema.pl"
                self.runner = []
                vers_cmd = ["perl", "-e", 'print "Perl $^V\n"']
            case "plpgsql":
                self.output = "schema.sql"
                self.runner = ["run_plpgsql.sh"]
                vers_cmd = ["psql", "--version"]
            case _:
                raise RunnerError(f"unexpected language: {language}")

        self.language_version = get_version(vers_cmd)
        self.jsu_version = get_version(["jsu-compile", "--version"])

        TMP.mkdir(exist_ok=True)

    def compile_schema(self, schema: JsonObject) -> Path:
        """Compile a schema for the current language."""

        schema_file = tmp_json_file("schema.json", schema)
        output_file = TMP / self.output

        subprocess.run([  # noqa: S603 S607
            "jsu-compile",
                "--no-fix",
                "--cache", str(CACHE),
                "--schema-version", str(self.version or 7),
                "-o", str(output_file),
                    str(schema_file),
        ], text=True, check=True)

        return output_file

    def run_test(self, validator: Path, test: Json) -> bool:
        """Run test using generated validator."""

        test_file = tmp_json_file("test.json", test)
        ps = subprocess.run(  # noqa: S603
            self.runner + [ str(validator), str(test_file) ],
            text=True, capture_output=True, check=True,
        )

        if "FAIL" in ps.stdout:
            return False
        elif "PASS" in ps.stdout:
            return True
        else:
            raise RunnerError(f"unexpected validation output: {ps.output}")

    def cmd_start(self, req: JsonObject) -> JsonObject:
        """Respond to start with various meta data about the implementation."""

        assert req.get("version") == 1, "expecting protocol version 1"

        return {
            "version": 1,
            "implementation": {
                "language": self.language,
                "language_version": self.language_version,
                "name": "jsu-compile",
                "version": self.jsu_version,
                "homepage": "https://github.com/zx80/json-schema-utils/",
                "documentation": "https://github.com/zx80/json-schema-utils/",
                "issues": "https://github.com/zx80/json-schema-utils/issues",
                "source": "https://github.com/zx80/json-schema-utils.git",
                "dialects": sorted(VERSIONS.keys()),
                "os": platform.system(),
                "os_version": platform.release(),
            },
        }

    def cmd_dialect(self, req: JsonObject) -> JsonObject:
        """Set current JSON Schema dialect, needed for schema semantics."""

        assert "dialect" in req, "dialect command expects a dialect"

        try:
            self.version = VERSIONS[req["dialect"]]
        except KeyError:  # unknown version
            self.version = 0

        return {"ok": True}

    def cmd_run(self, req: JsonObject) -> JsonObject:
        """Run one case and its tests."""

        case = req["case"]
        assert isinstance(case, dict), "case is an object"
        jschema = case["schema"]
        assert isinstance(jschema, (bool, dict)), "boolean or object schema"
        tests = case["tests"]
        assert isinstance(tests, list), "tests is a list of instances"
        description = case.get("description")
        assert description is None or isinstance(description, str)

        CACHE.mkdir(exist_ok=True)
        results: JsonArray = []

        try:
            # put registries in cache
            for reg in [SPECS, case.get("registry")]:
                if reg is not None:
                    for url, schema in reg.items():
                        # use truncated hashed url as filename
                        uh = hashlib.sha3_256(url.encode()).hexdigest()[:16]
                        with Path.open(CACHE / f"{uh}.json", "w") as fp:
                            json.dump(schema, fp)

            validator = self.compile_schema(jschema)

            # apply to test vector
            results = [
                {"valid": self.run_test(validator, test["instance"])}
                    for test in tests
            ]

        except Exception:  # an internal error occurred
            return {
                "errored": True,
                "seq": req["seq"],
                "context": {"traceback": traceback.format_exc()},
            }

        finally:  # wipe out cache to avoid state leaks
            shutil.rmtree(CACHE)

        return {
            "seq": req["seq"],
            "results": results,
        }

    def cmd_stop(self, req: JsonObject) -> JsonObject:
        """Stop all processing."""
        sys.exit(0)

    def process(self, req: JsonObject) -> JsonObject:
        """Process one request."""

        cmd = req["cmd"]
        match cmd:
            case "start":
                return self.cmd_start(req)
            case "dialect":
                return self.cmd_dialect(req)
            case "run":
                return self.cmd_run(req)
            case "stop":
                return self.cmd_stop(req)
            case _:  # trigger crash
                raise RunnerError(f"unexpected bowtie command cmd={cmd}")

    def run(self):
        """Runner purpose is to run."""

        # request/response protocol is to receive and send one-line jsons
        for line in sys.stdin:
            self.line += 1
            try:
                req = json.loads(line)
                assert isinstance(req, dict), "input must be a json object"
                res = self.process(req)
            except Exception as e:
                sys.stderr.write(f"{self.line}: invalid json input ({e})\n")
                sys.stderr.flush()
                raise  # voluntary crash
            sys.stdout.write(json.dumps(res))
            sys.stdout.write("\n")
            sys.stdout.flush()


if __name__ == "__main__":
    language = "python" if len(sys.argv) <=1 else sys.argv[1]
    Runner(language).run()
