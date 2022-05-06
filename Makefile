
CONTAINER_ENGINE=docker # no podman for now, due to mmap issues on macs. Should be ok to change on linux envs.

run_fuzz:
	pytest schemathesis_tests -s

build_kcp_image:
	pushd kcp && \
	$(CONTAINER_ENGINE) build -t localhost/kcp -f ../dockerfiles/kcp.Dockerfile . && \
	popd

submodules:
	git submodule update --init --remote

install_python_deps:
	touch schemathesis/setup.cfg && \
	pip install -r requirements.txt && \
	rm schemathesis/setup.cfg
