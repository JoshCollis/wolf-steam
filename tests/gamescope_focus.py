#!/usr/bin/env python3
"""Headless Gamescope focus regression. Run on a GPU test host."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import uuid


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', default='ghcr.io/joshcollis/wolf-steam:latest')
    p.add_argument('--card', default='/dev/dri/card0')
    p.add_argument('--render', default='/dev/dri/renderD128')
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    token = 'steam-focus-' + uuid.uuid4().hex[:12]
    out = args.output or Path(__file__).resolve().parents[1] / 'artifacts' / token
    out.mkdir(parents=True, exist_ok=False)
    report = {'image': args.image, 'cases': [], 'pixel_proof': False}
    containers = []
    local = None

    def run(argv, timeout=45, check=True, **kw):
        return subprocess.run(argv, text=True, capture_output=True,
                              timeout=timeout, check=check, **kw)

    try:
        client = Path(__file__).with_name('gamescope_focus_client.py')
        local = tempfile.TemporaryDirectory(prefix=token + '-')
        source = str(Path(local.name) / 'client.py')
        Path(source).write_bytes(client.read_bytes())
        for mode, flags in [('without_e', []), ('with_e', ['-e'])]:
            name = token + '-' + mode
            containers.append(name)
            command = ['docker', 'run', '--rm', '--name', name, '--network', 'none',
                       '--cpus', '1', '--memory', '1g', '--pids-limit', '128',
                       '--device', args.render, '--device', args.card,
                       '--tmpfs', '/probe:mode=0700', '-v', source + ':/fixture.py:ro,Z',
                       '-e', 'HOME=/probe', '-e', 'XDG_RUNTIME_DIR=/probe',
                       '-e', 'PATH=/usr/games:/usr/local/bin:/usr/bin:/bin',
                       '--entrypoint', '/usr/games/gamescope', args.image,
                       '--backend', 'headless', '-W', '640', '-H', '480', '--debug-focus',
                       *flags, '--', 'python3', '/fixture.py']
            result = run(command, check=False)
            (out / (mode + '.log')).write_text(result.stdout + result.stderr)
            assert result.returncode == 0, f'{mode} failed: see {out}'
            payloads = [line.split('=', 1)[1] for line in result.stdout.splitlines()
                        if line.startswith('FOCUS_RESULT=')]
            assert len(payloads) == 1, 'Expected exactly one fixture result'
            report['cases'].append({'mode': mode, 'result': json.loads(payloads[0])})
        old, new = [case['result'] for case in report['cases']]
        assert set(old['initial']['GAMESCOPE_FOCUSABLE_APPS']) == set(old['windows'].values())
        assert all(r['GAMESCOPE_FOCUSED_WINDOW'] == [old['windows']['game']] for r in old['requests'])
        assert set(new['initial']['GAMESCOPE_FOCUSABLE_APPS']) == {769, 2968420}
        for request in new['requests']:
            expected = new['windows']['steam' if request['requested'] == 769 else 'game']
            assert request['GAMESCOPE_FOCUSED_WINDOW'] == [expected]
            assert request['GAMESCOPE_FOCUSED_APP'] == [request['requested']]
        report['assertions_passed'] = True
        print('PASS: reproduced failed Steam-ID handoff without -e; all handoffs pass with -e')
    finally:
        # Clean only uniquely named containers and the single owned fixture file.
        for name in containers:
            run(['docker', 'rm', '-f', name], check=False)
        if local:
            local.cleanup()
        left = run(['docker', 'ps', '-a', '--filter', 'name=' + token,
                    '--format', '{{.Names}}']).stdout.strip()
        report['cleanup_verified'] = not left
        (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
        print('Evidence:', out)
        assert not left, 'Owned probe containers remain: ' + left


if __name__ == '__main__':
    main()
