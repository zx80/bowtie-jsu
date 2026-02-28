#! /usr/bin/env python3

"""
A Bowtie harness for the json-schema-utils schema validator
using the dynamic json-model-compiler Python backend.
"""

from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
import hashlib
import json
import platform
import sys
import traceback

from jsonschema_specifications import REGISTRY
from jsutils import json_schema_to_python_checker

type Jsonable = (
    None | bool | int | float | str | list[Jsonable] | dict[str, Jsonable]
)

# available JSON Schema specifications
SPECS: dict[str, Jsonable] = {url: REGISTRY.contents(url) for url in REGISTRY}

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
CACHE: str = "./schema-cache-by-hashed-urls"

# version for both front-end and back-end
JSU_VERSION: str = (
    f"{metadata.version('json-schema-utils')}"
    f" (backend jmc {metadata.version('json_model_compiler')})"
)


class RunnerError(Exception):
    pass


@dataclass
class Runner:
    # current dialect, but for older dialects only
    version: int | None = None

    # count input lines for some error messages
    line: int = 0

    def cmd_start(self, req: Jsonable) -> Jsonable:
        """Respond to start with various meta data about the implementation."""

        assert req.get("version") == 1, "expecting protocol version 1"

        return {
            "version": 1,
            "implementation": {
                "language": "python",
                "language_version": platform.python_version(),
                "name": "jsu",
                "version": JSU_VERSION,
                "homepage": "https://github.com/zx80/json-schema-utils/",
                "documentation": "https://github.com/zx80/json-schema-utils/",
                "issues": "https://github.com/zx80/json-schema-utils/issues",
                "source": "https://github.com/zx80/json-schema-utils.git",
                "dialects": sorted(VERSIONS.keys()),
                "os": platform.system(),
                "os_version": platform.release(),
            },
        }

    def cmd_dialect(self, req: Jsonable) -> Jsonable:
        """Set current JSON Schema dialect, needed for schema semantics."""

        try:
            self.version = VERSIONS[req["dialect"]]
        except Exception:  # unknown version
            self.version = 0

        return {"ok": True}

    def cmd_run(self, req: Jsonable) -> Jsonable:
        """Run one case and its tests."""

        case = req["case"]
        assert isinstance(case, dict)
        description = case.get("description")

        files, results = [], []

        try:
            # put registries in cache
            for reg in [SPECS, case.get("registry")]:
                if reg is not None:
                    for url, schema in reg.items():
                        # use truncated hashed url as filename
                        uh = hashlib.sha3_256(url.encode()).hexdigest()[:16]
                        fn = f"{CACHE}/{uh}.json"
                        files.append(fn)
                        with Path.open(fn, "w") as fp:
                            json.dump(schema, fp)

            # compile schema to python
            checker = json_schema_to_python_checker(
                case["schema"],
                description,
                cache=CACHE,
                version=self.version,
            )

            # apply to test vector
            results = [
                {"valid": checker(test["instance"])} for test in case["tests"]
            ]

        except Exception:  # an internal error occurred
            return {
                "errored": True,
                "seq": req.get("seq"),
                "context": {"traceback": traceback.format_exc()},
            }

        finally:
            # remove registered files from cache
            for fn in files:
                Path(fn).unlink()

        return {
            "seq": req.get("seq"),
            "results": results,
        }

    def cmd_stop(self, req: Jsonable) -> Jsonable:
        """Stop all processing."""
        sys.exit(0)

    def process(self, req: Jsonable) -> Jsonable:
        """Process one request."""

        cmd = req.get("cmd", "run")  # default is to run
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
    Runner().run()
