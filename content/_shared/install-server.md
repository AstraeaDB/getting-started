AstraeaDB is written in Rust, so you install it with `cargo`, which is Rust's
package and build tool. If you do not already have Rust, get it from
[rustup.rs](https://rustup.rs).

Building it also relies on Protocol Buffers, a data format from Google, so on a
fresh Linux machine you first need a few system packages. On Debian or Ubuntu,
one command installs all of them:

<!-- verify: skip reason="proven by the container image build, which runs this exact line from scratch in --mode install; re-running it per lesson would reinstall the same packages every time" -->
```bash
sudo apt-get install -y protobuf-compiler libprotobuf-dev pkg-config libssl-dev build-essential
```

On macOS with [Homebrew](https://brew.sh), the equivalent is `brew install
protobuf`. With those in place, install the server:

<!-- verify: skip reason="proven by the container image build, which runs this exact line from scratch in --mode install; re-running it per lesson would reinstall the same package every time" -->
```bash
# Installs the `astraeadb` command. The package is named astraea-cli, and
# the program it installs is called astraeadb.
cargo install astraea-cli

# Start the server (JSON/TCP on 127.0.0.1:7687, data persisted to disk)
astraeadb serve
```

Leave that terminal running, because it is now your database.
