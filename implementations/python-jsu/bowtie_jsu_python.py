#! /usr/bin/env python3
#
# Implement the bowtie protocol against json-schema-utils schema
# validator based on the dynamic json-model-compiler python backend.
#

# stupidly sorted imports
from dataclasses import dataclass
from importlib.metadata import version as pkg
from pathlib import Path
import hashlib
import json
import platform
import sys
import traceback

# JSON Schema Utils Compiler
from jsutils import json_schema_to_python_checker

type Jsonable = (
    None | bool | int | float | str | list[Jsonable] | dict[str, Jsonable]
)

# JSON Schema version URL to version
VERSIONS: dict[str, int] = {
    "https://json-schema.org/draft/2020-12/schema": 9,
    "https://json-schema.org/draft/2019-09/schema": 8,
    "http://json-schema.org/draft-07/schema#": 7,
    "http://json-schema.org/draft-06/schema#": 6,
    "http://json-schema.org/draft-04/schema#": 4,
    "http://json-schema.org/draft-03/schema#": 3,
}

DRAFT_2019_09  = 8

# cache is used for registry and meta schemas
CACHE: str = "."


@dataclass
class Runner:
    # current dialect, but for older dialects only
    version: int | None = None

    # count input lines for some error messages
    line: int = 0

    def cmd_start(self, req: Jsonable) -> Jsonable:
        assert req.get("version", 1) == 1, "expecting protocol version 1"

        # version for both front-end and back-end
        jsu_version = (
            f"{pkg('json-schema-utils')}"
            f" (backend jmc {pkg('json_model_compiler')})"
        )

        return {
            "version": 1,
            "implementation": {
                "language": "python",
                "language_version": platform.python_version(),
                "name": "jsu",
                "version": jsu_version,
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
            # however, 2019-09 and 2020-12 must rely on $schema
            if self.version >= DRAFT_2019_09:
                self.version = None
        except Exception:  # unknown version
            self.version = 0
        return {"ok": self.version != 0}

    def cmd_run(self, req: Jsonable) -> Jsonable:
        """Run one case and its tests."""

        case = req["case"]
        assert isinstance(case, dict)
        description = case.get(
            "description", f"case from input line {self.line}",
        )

        # put registry in cache
        registry = case.get("registry", {})
        if isinstance(registry, dict):  # may be set to null
            for url, schema in registry.items():
                uh: str = hashlib.sha3_256(url.encode()).hexdigest()[:16]
                with Path.open(f"{CACHE}/{uh}.json", "w") as fp:
                    json.dump(schema, fp)

        # TODO what about skipping unsupported cases?
        # FIXME there is no clean way to identify them

        try:
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

            return {
                "seq": req.get("seq", f"input line {self.line}"),
                "results": results,
            }
        except Exception:  # an internal error occurred
            return {
                "errored": True,
                "seq": req.get("seq", f"input line {self.line}"),
                "context": {"traceback": traceback.format_exc()},
            }

    def cmd_stop(self, req: Jsonable) -> Jsonable:
        """Stop all processing."""
        sys.exit(0)

    def process(self, req: Jsonable) -> Jsonable:
        """Process one request."""
        cmd = req.get("cmd", "run")  # default is to run
        return (
            self.cmd_start(req)
            if cmd == "start"
            else self.cmd_dialect(req)
            if cmd == "dialect"
            else self.cmd_run(req)
            if cmd == "run"
            else self.cmd_stop(req)
            if cmd == "stop"
            else {
                "errored": True,
                "seq": req.get("seq", f"input line {self.line}"),
                "message": f"unexpected bowtie command cmd={cmd}",
            }
        )

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
                res = {
                    "errored": True,
                    "message": f"invalid json input on line {self.line}: {e}",
                    "context": {"traceback": traceback.format_exc()},
                }
            sys.stdout.write(json.dumps(res))
            sys.stdout.write("\n")
            sys.stdout.flush()



if __name__ == "__main__":
    Runner().run()
