#!/usr/bin/env python3
"""Summarize the raw evdev records printed by the RAM `touch-events` script."""
import argparse
import json
import re
from pathlib import Path

RECORD = re.compile(r'^(?:[0-9a-f]{8} ){4}type=(\d+) code=(\d+) value=(-?\d+)\r?$', re.M)
EV_SYN, EV_KEY, EV_ABS = 0, 1, 3
ABS_MT_SLOT, ABS_MT_POSITION_X, ABS_MT_POSITION_Y, ABS_MT_TRACKING_ID = 47, 53, 54, 57


def summarize(text):
    slot, active, frames, contacts = 0, {}, 0, []
    max_fingers, xs, ys = 0, [], []
    for kind, code, value in ((int(a), int(b), int(c)) for a, b, c in RECORD.findall(text)):
        if kind == EV_ABS and code == ABS_MT_SLOT:
            slot = value
        elif kind == EV_ABS and code == ABS_MT_TRACKING_ID:
            if value < 0:
                contact = active.pop(slot, None)
                if contact:
                    contact['released'] = True
            else:
                active[slot] = {'slot': slot, 'tracking_id': value, 'points': 0, 'released': False}
                contacts.append(active[slot])
        elif kind == EV_ABS and code in (ABS_MT_POSITION_X, ABS_MT_POSITION_Y):
            contact = active.get(slot)
            if contact:
                axis = 'x' if code == ABS_MT_POSITION_X else 'y'
                contact.setdefault('first', {}).setdefault(axis, value)
                contact.setdefault('last', {})[axis] = value
                (xs if axis == 'x' else ys).append(value)
        elif kind == EV_SYN and code == 0:
            frames += 1
            max_fingers = max(max_fingers, len(active))
            for contact in active.values():
                contact['points'] += 1
    return {'records': len(RECORD.findall(text)), 'frames': frames, 'contacts': len(contacts),
            'max_simultaneous': max_fingers, 'all_released': all(c['released'] for c in contacts),
            'x_range': [min(xs), max(xs)] if xs else None, 'y_range': [min(ys), max(ys)] if ys else None,
            'contact_list': contacts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    print(json.dumps(summarize(parser.parse_args().log.read_text(errors='replace')), indent=1))


if __name__ == '__main__':
    main()
