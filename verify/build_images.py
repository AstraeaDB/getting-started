#!/usr/bin/env python3
"""Build the four verification container images.

    python3 verify/build_images.py --mode fast
    python3 verify/build_images.py --mode install
    python3 verify/build_images.py --mode install --ref 4536c72

Two modes, and the split is the point (DESIGN.md 7.2):

  install   Rebuild from scratch with no cache. This runs the exact apt-get and
            cargo install lines the Crawl lessons print, so building the image
            IS the test of the install instructions. Takes several minutes.
            Run it on a release, and on any change to _shared/install-server.md.

  fast      Reuse cached layers. Seconds, not minutes. This is what runs while
            someone is iterating on a lesson.

Without that split, "verification is too slow to run" quietly becomes
"verification does not run".
"""

import argparse
import subprocess
import sys
from pathlib import Path

VERIFY = Path(__file__).resolve().parent
BIN = VERIFY / "bin"

IMAGES = [
    ("astraea-verify-base", "Dockerfile.base"),
    ("astraea-verify-py", "Dockerfile.py"),
    ("astraea-verify-r", "Dockerfile.r"),
    ("astraea-verify-rust", "Dockerfile.rust"),
]


def die(msg):
    print(f"images: error: {msg}", file=sys.stderr)
    sys.exit(1)


def run(argv, **kw):
    print("images: $ " + " ".join(str(a) for a in argv), flush=True)
    return subprocess.run(argv, **kw)


def extract_binary():
    """Pull the linux binary out of the base image into the build context.

    Dockerfile.r starts FROM r-base rather than from our base, so it needs the
    astraeadb binary from somewhere. `COPY --from=astraea-verify-base` does not
    work: buildkit reads the name as a registry reference and tries to pull it
    from Docker Hub, which 401s. Extracting to the build context is the way
    that actually works here.
    """
    BIN.mkdir(exist_ok=True)
    out = BIN / "astraeadb"
    with out.open("wb") as fh:
        proc = subprocess.run(
            ["container", "run", "--rm", "astraea-verify-base",
             "cat", "/root/.cargo/bin/astraeadb"],
            stdout=fh, stderr=subprocess.PIPE,
        )
    if proc.returncode != 0 or out.stat().st_size < 1_000_000:
        die(f"could not extract astraeadb from the base image: {proc.stderr.decode()[:300]}")
    out.chmod(0o755)
    print(f"images: extracted {out.relative_to(VERIFY.parent)} "
          f"({out.stat().st_size // 1024} KB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=("fast", "install"), default="fast")
    ap.add_argument("--ref", default="main",
                    help="AstraeaDB git ref to install from (install mode)")
    ap.add_argument("--only", nargs="*", help="build only these image names")
    args = ap.parse_args()

    if not VERIFY.joinpath("Dockerfile.base").is_file():
        die("run from the project root; verify/Dockerfile.base not found")

    targets = IMAGES
    if args.only:
        names = {n for n, _ in IMAGES}
        unknown = [o for o in args.only if o not in names]
        if unknown:
            die(f"unknown image(s): {unknown}")
        targets = [(n, d) for n, d in IMAGES if n in args.only]

    for name, dockerfile in targets:
        argv = ["container", "build", "-t", name, "-f", dockerfile]
        if args.mode == "install":
            # No cache, so the install lines really do run from scratch.
            argv.append("--no-cache")
        if name == "astraea-verify-base":
            argv += ["--build-arg", f"ASTRAEADB_REF={args.ref}"]
        argv.append(".")

        proc = run(argv, cwd=VERIFY)
        if proc.returncode != 0:
            die(f"{name} failed to build (exit {proc.returncode})")
        print(f"images: {name} ok")

        # The R image needs the binary that only exists once base is built.
        if name == "astraea-verify-base":
            extract_binary()

    print(f"images: {len(targets)} image(s) built in {args.mode} mode")


if __name__ == "__main__":
    main()
