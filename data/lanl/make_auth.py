#!/usr/bin/env python3
"""Build the authentication file used by run-03.

IMPORTANT, AND SAID PLAINLY: the benign events in `auth.csv` are SYNTHETIC.
The 25 red-team events mixed into them are REAL, taken verbatim from the LANL
dataset's own ground-truth labels.

Why synthesise anything. The LANL authentication file is tens of gigabytes, and
the slice this site ships is DNS only. Without benign authentications there is
no haystack, and a hunt that finds the needle in an empty field teaches nothing.
So benign traffic is derived from the real DNS structure: a machine that looks
up a server is a machine whose users plausibly authenticate to that server.

What is real and what is not:

  REAL      the 25 red-team events, their users, machines and timestamps
  REAL      the DNS graph the benign traffic is derived from
  SYNTHETIC which user sits at which machine, and the benign auth events

The attack signature the lesson hunts for is therefore genuine: five credentials
fanning out from two machines is what the labelled data actually contains. The
normal behaviour it stands out against is manufactured, and deliberately
unexciting.

Deterministic: seeded, so the same input always gives the same output.

Usage:
    python3 make_auth.py            # writes auth.csv beside this script
"""
import csv
import collections
import pathlib
import random

HERE = pathlib.Path(__file__).parent
SEED = 20260810
USERS_PER_MACHINE = (1, 2)      # a normal machine has one or two regular users
AUTHS_PER_USER = (2, 6)         # each of whom reaches a handful of servers


def main():
    rng = random.Random(SEED)
    dns = list(csv.reader((HERE / "dns.csv").open()))
    redteam = list(csv.reader((HERE / "redteam.csv").open()))

    # Who talks to whom, and when, straight from the real DNS graph.
    resolves = collections.defaultdict(set)
    times = collections.defaultdict(list)
    for t, src, dst in dns:
        resolves[src].add(dst)
        times[src].append(int(t))

    clients = sorted(c for c in resolves if resolves[c])
    rows = []

    attack_start = min(int(r[0]) for r in redteam)

    def benign_for(user, machine, before=None):
        """Ordinary activity: this user, at this machine, reaching servers that
        machine actually resolves.

        `before` caps the timestamps. Red-team accounts get their home-machine
        activity placed before the intrusion begins, because that is the shape
        of a stolen credential: the account was working normally, and then it
        appeared somewhere it had never been. Without that ordering a
        time-travel query cannot show the change.
        """
        targets = sorted(resolves[machine])
        if not targets:
            return
        pool = [t for t in times[machine] if before is None or t < before]
        if not pool:
            return
        picks = rng.sample(targets, min(len(targets), rng.randint(*AUTHS_PER_USER)))
        for dst in picks:
            rows.append([rng.choice(pool), user, machine, dst])

    # Give every red-team account a normal home machine first. These are real
    # accounts belonging to real people; the intrusion is a credential of theirs
    # being used from somewhere it does not belong. Without a home machine the
    # hunt would be finding accounts that exist only in the attack, which is not
    # what a stolen credential looks like.
    real_users = sorted({r[1] for r in redteam})
    attacker_machines = {r[2] for r in redteam}
    # A home machine has to have been active before the intrusion, or there is
    # no "normally" for the account to have been doing something during.
    eligible = [c for c in clients
                if c not in attacker_machines
                and any(t < attack_start for t in times[c])]
    homes = rng.sample(eligible, len(real_users))
    for user, machine in zip(real_users, homes):
        benign_for(user, machine, before=attack_start)

    # Then ordinary users, numbered so they cannot collide with a real account.
    taken = {u.split("@")[0] for u in real_users}
    next_user = 40000
    for machine in clients:
        for _ in range(rng.randint(*USERS_PER_MACHINE)):
            while f"U{next_user}" in taken:
                next_user += 1
            benign_for(f"U{next_user}@DOM1", machine)
            next_user += 1

    rows.extend(redteam)                     # the real ones, unmodified
    rows.sort(key=lambda r: int(r[0]))

    with (HERE / "auth.csv").open("w", newline="") as fh:
        csv.writer(fh).writerows(rows)

    users = {r[1] for r in rows}
    print(f"{len(rows)} auth events ({len(rows) - len(redteam)} synthetic benign, "
          f"{len(redteam)} real red-team), {len(users)} users")


if __name__ == "__main__":
    main()
