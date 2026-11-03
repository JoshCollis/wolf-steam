import importlib.util
import pathlib
import re
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("package_evidence", ROOT / "build/package-evidence.py")
EVIDENCE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EVIDENCE)


class RefreshPolicyTests(unittest.TestCase):
    def test_support_gate_release_and_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            release = pathlib.Path(directory) / "os-release"
            for distro, version, day, supported in [
                ("ubuntu", "26.04", "2026-11-03", True),
                ("ubuntu", "26.04", "2031-05-31", True),
                ("ubuntu", "26.04", "2031-06-01", False),
                ("ubuntu", "26.10", "2026-11-03", False),
                ("debian", "26.04", "2026-11-03", False),
                ("ubuntu", "26.04", "", False),
            ]:
                with self.subTest(distro=distro, version=version, day=day):
                    release.write_text(f'ID={distro}\nVERSION_ID="{version}"\n')
                    result = subprocess.run(["bash", str(ROOT / "build/check-support.sh"), str(release), day],
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode == 0, supported, result.stderr)

    def test_both_stages_share_pinned_lts_and_refresh_packages(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertRegex(dockerfile, r"ARG BASE_IMAGE=ubuntu:26\.04@sha256:[0-9a-f]{64}\n")
        self.assertEqual(re.findall(r"^FROM (.*)$", dockerfile, re.M),
                         ["${BASE_IMAGE} AS probe-builder", "${BASE_IMAGE} AS runtime"])
        for stage in dockerfile.split("FROM ${BASE_IMAGE}")[1:]:
            self.assertIn("bash /tmp/check-support.sh", stage)
            self.assertIn('test "$(dpkg --print-architecture)" = amd64', stage)
            self.assertIn("dpkg --add-architecture i386", stage)
            self.assertIn("apt-get -o APT::Update::Error-Mode=any update", stage)
            self.assertIn("Always-Include-Phased-Updates=true upgrade -y --with-new-pkgs", stage)
            self.assertLess(stage.index(" upgrade "), stage.index("apt-get install"))
        for package in ("steam-libs", "mesa-vulkan-drivers", "libgl1-mesa-dri", "libvulkan1"):
            for arch in ("amd64", "i386"):
                self.assertIn(f"{package}:{arch}", dockerfile)
        self.assertLess(dockerfile.index("python3 /tmp/package-evidence.py"),
                        dockerfile.index("rm -rf /var/lib/apt/lists"))
        for label in ("base.name=$BASE_IMAGE", "base.digest=$BASE_DIGEST", "revision=$IMAGE_REVISION"):
            self.assertIn("org.opencontainers.image." + label, dockerfile)

    def test_schedule_resolves_official_base_without_dependency_cache(self):
        workflow = (ROOT / ".github/workflows/image.yml").read_text()
        self.assertIn("cron: '43 5 * * 1'", workflow)
        self.assertIn("docker pull --platform linux/amd64 ubuntu:26.04", workflow)
        self.assertIn("docker image inspect ubuntu:26.04", workflow)
        self.assertIn('[[ "$base" =~ ^ubuntu@sha256:[0-9a-f]{64}$ ]]', workflow)
        self.assertIn("docker build --platform linux/amd64 --pull --no-cache", workflow)
        self.assertIn('--build-arg BASE_IMAGE="$base" --build-arg BASE_DIGEST="${base#*@}"', workflow)
        self.assertNotIn("cache-from", workflow)

    def test_only_main_publishes_exact_tested_image_with_unique_run_tag(self):
        workflow = (ROOT / ".github/workflows/image.yml").read_text()
        gate = "if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'"
        self.assertEqual(workflow.count(gate), 2)
        self.assertLess(workflow.index("run: bash tests/verify-image.sh"), workflow.index("- name: Log in to GHCR"))
        self.assertIn("IMAGE: wolf-steam:ci", workflow)
        self.assertEqual(workflow.count("docker build --"), 1)
        self.assertIn('docker tag wolf-steam:ci "${image}:${tag}"', workflow)
        self.assertIn('for tag in "sha-${REVISION}" main latest "$RUN_TAG"', workflow)
        self.assertIn("RUN_TAG: run-${{ github.run_id }}-${{ github.run_attempt }}", workflow)
        self.assertIn("password: ${{ secrets.GITHUB_TOKEN }}", workflow)
        for uses in re.findall(r"uses: (\S+)", workflow):
            self.assertRegex(uses, r"@[0-9a-f]{40}$")

    def collect(self, candidate="1.2", audit="", installed=None):
        if installed is None:
            installed = "libvulkan1:amd64\t1.2\tamd64\tinstalled\nlibvulkan1:i386\t1.2\ti386\tinstalled\n"

        def command(*args):
            if args[0] == "dpkg":
                return "amd64\n" if args[1] == "--print-architecture" else audit
            if args[0] == "dpkg-query":
                return installed
            return "".join(f"{name.removesuffix(':amd64')}:\n  Installed: 1.2\n  Candidate: {candidate}\n"
                           for name in args[2:])

        with mock.patch.object(EVIDENCE, "command", side_effect=command):
            return EVIDENCE.collect()

    def test_candidate_evidence_includes_each_architecture(self):
        packages, policies = self.collect()
        self.assertEqual([package["architecture"] for package in packages], ["amd64", "i386"])
        self.assertTrue(all(package["installed"] == package["candidate"] for package in packages))
        self.assertIn("libvulkan1:i386", policies)

    def test_stale_or_missing_candidate_fails(self):
        for candidate in ("1.3", "(none)", ""):
            with self.subTest(candidate=candidate), self.assertRaises(RuntimeError):
                self.collect(candidate=candidate)

    def test_incomplete_or_empty_package_state_fails(self):
        with self.assertRaises(RuntimeError):
            self.collect(audit="unconfigured package")
        with self.assertRaises(RuntimeError):
            self.collect(installed="")
