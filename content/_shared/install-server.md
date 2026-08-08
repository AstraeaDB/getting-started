AstraeaDB is written in Rust, so building the server needs Rust's build tools from [rustup.rs](https://rustup.rs). Building also relies on Protocol Buffers, so on Debian or Ubuntu one command installs the system packages:

```bash
sudo apt-get install -y protobuf-compiler libprotobuf-dev pkg-config libssl-dev build-essential
```
