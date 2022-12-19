import logging
import pytest
from typing import Tuple, Any, Dict
from algosdk.account import generate_account
from algosdk.v2client.algod import AlgodClient

from kavm.algod import KAVMClient

from kcoin_vault.client import ContractClient
from kcoin_vault.sandbox import get_accounts



def pytest_addoption(parser):
    parser.addoption("--pyteal-code-module-str", action="store", default="default name")
    parser.addoption(
        '--backend',
        action='store',
        default='algod',
        choices=['kavm', 'sandbox'],
        help='AVM implementaion to run tests against',
    )


@pytest.fixture(scope="session")
def algod(request: Any, creator_account) -> AlgodClient | KAVMClient:
    if request.config.getoption('--backend') == 'sandbox':
        return AlgodClient("a" * 64, "http://localhost:4001")
    else:
        return KAVMClient(faucet_address=creator_account['address'], log_level=logging.ERROR)


@pytest.fixture(scope="session")
def pyteal_code_module_str(pytestconfig):
    return pytestconfig.getoption("pyteal_code_module_str")


@pytest.fixture(scope="session")
def creator_account(request: Any) -> Dict[str, str]:
    if request.config.getoption('--backend') == 'sandbox':
        creator_addr, creator_private_key = get_accounts()[0]
        return {'address': creator_addr, 'private_key': creator_private_key}
    else:
        creator_private_key, creator_addr = generate_account()
        return {'address': str(creator_addr), 'private_key': creator_private_key}


@pytest.fixture(scope='session')
def initial_state_fixture(
    algod, creator_account, pyteal_code_module_str
) -> Tuple[ContractClient, str, str]:
    return (
        ContractClient(
            algod,
            creator_account['address'],
            creator_account['private_key'],
            pyteal_code_module_str,
        ),
        creator_account['address'],
        creator_account['private_key'],
    )
