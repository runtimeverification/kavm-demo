import logging
import pytest
from typing import Tuple
from algosdk.account import generate_account

from algosdk.account import generate_account
from kavm.algod import KAVMClient
from kcoin_vault.client import ContractClient

def pytest_addoption(parser):
    parser.addoption("--pyteal-code-module-str", action="store", default="default name")
    # parser.addoption("--log-level", action="store", default="default name")


@pytest.fixture(scope="session")
def pyteal_code_module_str(pytestconfig):
    return pytestconfig.getoption("pyteal_code_module_str")

# @pytest.fixture(scope="session")
# def log_level(pytestconfig):
#     return pytestconfig.getoption("log_level")

@pytest.fixture(scope='session')
def initial_state_fixture(pyteal_code_module_str) -> Tuple[ContractClient, str, str]:
    creator_private_key, creator_addr = generate_account()
    creator_addr = str(creator_addr)
    algod = KAVMClient(faucet_address=creator_addr, log_level=logging.ERROR)
    return ContractClient(algod, creator_addr, creator_private_key, pyteal_code_module_str), str(creator_addr), creator_private_key
