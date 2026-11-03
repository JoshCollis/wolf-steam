"""Record installed versions against fresh APT candidates; fail on any mismatch.

Run before deleting APT lists, immediately after update/upgrade/install. This is
repository snapshot evidence, not a promise of future freshness/security fixes.
"""
import datetime
import json
import os
import pathlib
import subprocess
import sys


def command(*args):
    return subprocess.check_output(args, text=True, env={**os.environ, "LC_ALL": "C"})


def collect():
    audit = command("dpkg", "--audit")
    if audit.strip():
        raise RuntimeError(f"Incomplete package state: {audit}")
    installed = command("dpkg-query", "-W", "-f=${binary:Package}\t${Version}\t${Architecture}\t${db:Status-Status}\n")
    rows = [line.split("\t") for line in installed.splitlines()]
    rows = [row for row in rows if row[3] == "installed"]
    if not rows:
        raise RuntimeError("No installed package evidence")
    native = command("dpkg", "--print-architecture").strip()
    # One query avoids reloading all amd64/i386 APT indexes per package.
    policies = command("apt-cache", "policy", *(row[0] for row in rows))
    candidates = {}
    name = None
    for line in policies.splitlines():
        if line and not line[0].isspace() and line.endswith(":"):
            name = line[:-1]
        elif name and line.strip().startswith("Candidate: "):
            candidates[name] = line.strip().removeprefix("Candidate: ")
    packages = []
    for name, version, architecture, _ in rows:
        # APT omits the native architecture qualifier in policy headings.
        key = name.removesuffix(f":{native}")
        candidate = candidates.get(key)
        if candidate != version:
            raise RuntimeError(f"{name}: installed {version}, candidate {candidate}; refresh required")
        packages.append(dict(package=name, architecture=architecture, installed=version, candidate=candidate))
    return packages, policies


def main():
    output = pathlib.Path(sys.argv[1])
    packages, policies = collect()
    evidence = dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    policy="Ubuntu 26.04 LTS repositories; standard support through May 2031",
                    packages=packages)
    (output / "packages.json").write_text(json.dumps(evidence, indent=2) + "\n")
    (output / "apt-policy.txt").write_text(policies)


if __name__ == "__main__":
    main()
