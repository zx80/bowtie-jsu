#! /usr/bin/env python3

from importlib.metadata import version as pkg
import sys
import platform
import traceback

from dataclasses import dataclass
import json
import hashlib

# JSON Schema Utils Compiler
from jsutils import json_schema_to_python_checker

type Jsonable = None|bool|int|float|str|list[Jsonable]|dict[str, Jsonable]

# JSON Schema version URL to version
VERSIONS: dict[str, int] = {
    "https://json-schema.org/draft/2020-12/schema": 9,
    "https://json-schema.org/draft/2019-09/schema": 8,
    "http://json-schema.org/draft-07/schema#": 7,
    "http://json-schema.org/draft-06/schema#": 6,
    "http://json-schema.org/draft-04/schema#": 4,
    "http://json-schema.org/draft-03/schema#": 3,
}

# cache is used for registry
CACHE: str = "."

@dataclass
class Runner:
    version: int|None = None
    started: bool = False
    commands: int = 0

    def cmd_start(self, req: Jsonable) -> Jsonable:
        self.started = True
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
        assert self.started, "must be started!"
        try:
            self.version = VERSIONS[req["dialect"]]
            if self.version >= 8:  # 2019-09 and 2020-12 must rely on $schema
                self.version = None
        except Exception:  # unknown version
            self.version = 0
        return { "ok": self.version != 0 }

    def cmd_run(self, req: Jsonable) -> Jsonable:
        """Run one case and its tests."""
        assert self.started, "must be started!"

        case = req["case"]
        assert isinstance(case, dict)
        description = case.get("description", f"run {self.commands}")

        # put registry in cache
        registry = case.get("registry", {})
        if isinstance(registry, dict):
            for url, schema in registry.items():
                uh: str = hashlib.sha3_256(url.encode()).hexdigest()[:16]
                with open(f"{CACHE}/{uh}.json", "w") as fp:
                    json.dump(schema, fp)

        # TODO what about skipping unsupported cases?
        # FIXME there is no clean way to identify them

        try:
            # compile schema to python
            checker = json_schema_to_python_checker(
                case["schema"], description, cache=CACHE, version=self.version,
            )

            # apply to test vector
            results = [
                {"valid": checker(test["instance"])} for test in case["tests"]
            ]

            return {
                "seq": req["seq"],
                "results": results,
            }
        except Exception:  # an internal error occurred
            return {
                "errored": True,
                "seq": req["seq"],
                "context": { "traceback": traceback.format_exc() },
            }

    def cmd_stop(self, req: Jsonable) -> Jsonable:
        """Stop all processing."""
        assert self.started, "must be started!"
        sys.exit(0)

    def process(self, req: Jsonable) -> Jsonable:
        """Process one request."""
        self.commands += 1
        cmd = req.get("cmd", "run")  # default is to run
        return (
            self.cmd_start(req) if cmd == "start" else
            self.cmd_dialect(req) if cmd == "dialect" else
            self.cmd_run(req) if cmd == "run" else
            self.cmd_stop(req) if cmd == "stop" else {
                "errored": True,
                "seq": req.get("seq", None),
                "message": f"unexpected command cmd={cmd}"
            }
        )

    def run(self):
        """Runner purpose is to run."""
        # request/response protocol is to receive and send one-line jsons
        for line in sys.stdin:
            req = json.loads(line)
            res = self.process(req)
            print(json.dumps(res), flush=True)

if __name__ == "__main__":
    Runner().run()
