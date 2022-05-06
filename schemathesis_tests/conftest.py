import os
import yaml
import shutil
from tempfile import mkdtemp
from pathlib import Path

import subprocess
from subprocess import PIPE

import requests
from requests.adapters import HTTPAdapter, Retry

import pytest
import schemathesis


ROOT_PATH = Path(__file__).parent.parent.absolute()
CONTAINER_ENGINE = os.getenv("CONTAINER_ENGINE", "docker")
RUN_KCP_CONTAINER = os.getenv("RUN_KCP", True)
IMAGE_NAME = "localhost/kcp"
CONTAINER_NAME = "fuzz_target"


@pytest.fixture(scope="session")
def base_url():
    return "https://127.0.0.1:6443/"


def wait_available(base_url: str, retries=10) -> None:
    print("Wait for KCP to be available")
    s = requests.Session()
    retries = Retry(
        total=retries,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )
    s.mount('https://', HTTPAdapter(max_retries=retries))
    s.get(f'{base_url}readyz', timeout=1, verify=False)


@pytest.fixture(scope="session", autouse=True)
def spin_kcp_in_container(request, base_url: str) -> str:
    if RUN_KCP_CONTAINER:
        print("Spin up KCP container")
        tmpdir = mkdtemp(prefix="kcp_fuzz", dir=ROOT_PATH)
        cmd = [
            CONTAINER_ENGINE,
            "run",
            "--rm",
            "-p", "6443:6443/tcp",
            "-p", "6443:6443/udp",
            "-v", f"{tmpdir}:/.kcp",
            "--name", CONTAINER_NAME,
            IMAGE_NAME,
            "./kcp", "start", "--logtostderr=false"
        ]
        popen = subprocess.Popen(cmd, stderr=PIPE)
        stderr = popen.stderr.readline().decode("utf-8")
        # ugly hack to ensure that kcp was started
        assert "--logtostderr has been deprecated" in stderr, "Failed to start kcp container"
        wait_available(base_url)

        def cleanup():
            cleanup_cmd = [
                "docker",
                "rm",
                "-f",
                CONTAINER_NAME
            ]
            cleanup_popen = subprocess.Popen(cleanup_cmd, stderr=PIPE)
            cleanup_popen.wait(10)
            # tmpdir should be removes strictly after container stop, otherwise it will break docker.
            shutil.rmtree(tmpdir, ignore_errors=True)

        request.addfinalizer(cleanup)
        yield tmpdir
        cleanup()
    else:
        raise NotImplementedError("External KCP does not implemented yet")


@pytest.fixture(autouse=True, scope="session")
def registered_auth_class(spin_kcp_in_container):
    kcp_tmpdir = spin_kcp_in_container
    KUBECONFIG_FILENAME = "admin.kubeconfig"

    @schemathesis.auth.register()
    class KubeconfigAuth:

        @staticmethod
        def get_token():
            # workaround for obtain token for pass it to `from_uri` schemathesis method
            with open((Path(kcp_tmpdir) / KUBECONFIG_FILENAME), "r") as fd:
                kubeconfig = fd.read()
                kubeconfig = yaml.safe_load(kubeconfig)
                token = kubeconfig['users'][0]['user']['token']
            return token

        def get(self, context):
            return self.get_token()

        def set(self, case, data, context):
            case.headers = {"Authorization": f"Bearer {data}"}

    return KubeconfigAuth


@pytest.fixture(scope="session")
def kcp(spin_kcp_in_container, registered_auth_class, base_url):
    auth_header = {"Authorization": f"Bearer {registered_auth_class.get_token()}"}
    return schemathesis.from_uri(f"{base_url}openapi/v2", headers=auth_header, verify=False)
