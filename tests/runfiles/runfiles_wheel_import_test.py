# Copyright 2026 The Bazel Authors. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import pathlib
import subprocess
import sys
import tempfile
import textwrap
import unittest
from typing import Optional


class RunfilesWheelImportTest(unittest.TestCase):
    def test_imports_bazel_runfiles_when_runfiles_module_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as conflicting_dir:
            pathlib.Path(conflicting_dir, "runfiles.py").write_text(
                "raise RuntimeError('imported conflicting runfiles module')\n",
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = os.pathsep.join([conflicting_dir, _find_wheel()])

            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    textwrap.dedent(
                        """\
                        from bazel_runfiles import Create, Runfiles

                        r = Create({"RUNFILES_DIR": "runfiles/root"})
                        assert isinstance(r, Runfiles)
                        assert r.Rlocation("pkg/file.txt") == "runfiles/root/pkg/file.txt"
                        """
                    ),
                ],
                check=True,
                env=env,
            )

    def test_imports_legacy_runfiles_module(self) -> None:
        env = os.environ.copy()
        env["PYTHONPATH"] = _find_wheel()

        subprocess.run(
            [
                sys.executable,
                "-c",
                textwrap.dedent(
                    """\
                    from runfiles import Create, Runfiles

                    r = Create({"RUNFILES_DIR": "runfiles/root"})
                    assert isinstance(r, Runfiles)
                    assert r.Rlocation("pkg/file.txt") == "runfiles/root/pkg/file.txt"
                    """
                ),
            ],
            check=True,
            env=env,
        )


def _find_wheel() -> str:
    wheel = os.environ.get("BAZEL_RUNFILES_WHEEL")
    if wheel:
        return wheel

    manifest_file = os.environ.get("RUNFILES_MANIFEST_FILE")
    if manifest_file:
        wheel_from_manifest = _find_wheel_in_manifest(pathlib.Path(manifest_file))
        if wheel_from_manifest:
            return wheel_from_manifest

    runfiles_root = os.environ.get("TEST_SRCDIR")
    if runfiles_root:
        wheels = list(pathlib.Path(runfiles_root).rglob("bazel_runfiles-*.whl"))
        if wheels:
            return str(wheels[0])

    raise FileNotFoundError("Could not find bazel_runfiles wheel in test runfiles")


def _find_wheel_in_manifest(manifest_file: pathlib.Path) -> Optional[str]:
    for line in manifest_file.read_text(encoding="utf-8").splitlines():
        runfiles_path, _, real_path = line.partition(" ")
        if (
            runfiles_path.endswith(".whl")
            and "/python/runfiles/bazel_runfiles-" in runfiles_path
        ):
            return real_path
    return None


if __name__ == "__main__":
    unittest.main()
