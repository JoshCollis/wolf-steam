#!/usr/bin/env python3
"""Gamescope session: parent wl_output is authoritative; never invent cadence."""
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

RATES = (60000, 90000, 120000, 144000)

def requested(env):
    values = [env.get(k, '') for k in ('GAMESCOPE_WIDTH', 'GAMESCOPE_HEIGHT', 'GAMESCOPE_REFRESH')]
    if any(not re.fullmatch(r'[0-9]+', v) for v in values):
        raise ValueError('Wolf must supply integer width, height and negotiated refresh')
    w, h, r = map(int, values)
    if not (320 <= w <= 7680 and 200 <= h <= 4320 and r * 1000 in RATES):
        raise ValueError('Unsupported negotiated mode; allowed refresh: 60/90/120/144')
    return w, h, r * 1000

def parent_mode(text):
    from decimal import Decimal
    modes = re.findall(r'width:\s*(\d+) px, height:\s*(\d+) px, refresh:\s*([0-9.]+) (mHz|Hz),?\s+flags:([^\n]+)', text)
    current = [(int(w), int(h), int(Decimal(r) * (1000 if unit == 'Hz' else 1))) for w,h,r,unit,flags in modes if 'current' in flags.split()]
    if len(current) != 1:
        raise ValueError('Expected exactly one advertised current parent wl_output mode')
    return current[0]

def agree(wanted, actual):
    if wanted != actual:
        raise ValueError(f'Negotiated {wanted} disagrees with parent {actual}; refusing cosmetic mode fix')
    return actual

def reconnect(previous, actual):
    w,h,r = actual
    requested({'GAMESCOPE_WIDTH':str(w),'GAMESCOPE_HEIGHT':str(h),'GAMESCOPE_REFRESH':str(r//1000)})
    if r not in RATES:
        raise ValueError('Unsupported parent refresh on reconnect')
    return actual

def config(mode):
    w,h,r = mode
    return f"""xwayland force
output * mode {w}x{h}@{r//1000}Hz position 0 0
seat * hide_cursor 3000
focus_follows_mouse no
default_border none
"""

def read_parent(env):
    result = subprocess.run(['wayland-info'], env=env, text=True, capture_output=True, timeout=8, check=True)
    return parent_mode(result.stdout)

def launch_args(mode, command):
    w,h,r = mode
    # Steam controls focus by app ID (769 for its UI), not X11 window ID.
    # Without Steam mode those requests cannot match Gamescope's app list.
    return ['/usr/games/gamescope','-e','-b','-W',str(w),'-H',str(h),'-w',str(w),'-h',str(h),'-r',str(r//1000),'--',*command]

def requires_recreation(previous, actual):
    return previous != reconnect(previous, actual)

def main():
    parent_env = os.environ.copy()
    mode = agree(requested(parent_env), read_parent(parent_env))
    if parent_env.get('RUN_SWAY', '').lower() in ('true','1','yes'):
        raise ValueError('RUN_SWAY is unsupported for negotiated refresh; use RUN_SWAY=false')
    env = parent_env.copy()
    env.pop('DISPLAY', None)
    command = sys.argv[1:] or ['/usr/games/steam','-bigpicture']
    sway = subprocess.Popen(launch_args(mode, command), env=env, start_new_session=True)
    print(f'parent mode verified, gamescope launched at negotiated rate: {mode}', flush=True)
    def stop(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        while sway.poll() is None:
            time.sleep(1)
            actual = read_parent(parent_env)
            if requires_recreation(mode, actual):
                print(f'parent changed {mode} -> {actual}; recreate lobby with fresh negotiation', file=sys.stderr)
                return 75
        return sway.returncode or 0
    finally:
        # Clean the entire isolated compositor/application process group.
        try:
            os.killpg(sway.pid, signal.SIGTERM)
            sway.wait(timeout=8)
        except subprocess.TimeoutExpired:
            os.killpg(sway.pid, signal.SIGKILL)
            sway.wait()
        except ProcessLookupError:
            pass

if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as error:
        print(f'whale-steam: {error}', file=sys.stderr)
        sys.exit(1)
