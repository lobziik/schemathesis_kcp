# Schemathesis + KCP

Simple experimental setup for run [Schemathesis](https://github.com/schemathesis/schemathesis/)
over [KCP](https://github.com/kcp-dev/kcp)

## How to run

Prerequisites:
    - Docker (podman on linux hosts should work in theory, but never tested)
    - Python 3.6+


Setup:
* Create virtualenv
* Init git submodules (`make submodules` as shortcut is there)
* Install python deps (`make install_python_deps`)
* Build KCP docker image (`make build_kcp_image`)
* Run schemathesis with `make run_fuzz`