import schemathesis


schema = schemathesis.from_pytest_fixture("kcp")


@schema.parametrize()
def test_api(case):
    case.call_and_validate(verify=False)
