import logging
from typing import Any, Dict, Tuple
import importlib

from algosdk.atomic_transaction_composer import AccountTransactionSigner
from beaker.sandbox.kmd import SandboxAccount

import pytest
from algosdk.account import generate_account
from algosdk.v2client.algod import AlgodClient
from beaker import sandbox

import algosdk.atomic_transaction_composer
import beaker.client.application_client
from kavm.algod import KAVMAtomicTransactionComposer

from kavm.algod import KAVMClient

from kcoin_vault.kcoin_vault_beaker_client import KCointVaultClient


def pytest_addoption(parser):
    parser.addoption("--pyteal-code-module-str", action="store", default="default name")
    parser.addoption(
        '--backend',
        action='store',
        default='algod',
        choices=['kavm', 'sandbox'],
        help='AVM implementaion to run tests against',
    )
    parser.addoption(
        '--methods',
        type=str,
        help='Method sequence to call',
    )


@pytest.fixture(scope="session")
def pyteal_code_module_str(pytestconfig):
    return pytestconfig.getoption("pyteal_code_module_str")


@pytest.fixture(scope="session")
def methods(pytestconfig):
    return pytestconfig.getoption("methods").split()


@pytest.fixture(scope="session")
def algod(request: Any, creator_account) -> AlgodClient | KAVMClient:
    if request.config.getoption('--backend') == 'sandbox':
        return AlgodClient("a" * 64, "http://localhost:4001")
    else:
        return KAVMClient(faucet_address=creator_account.address, log_level=logging.ERROR)


@pytest.fixture(scope="session")
def creator_account(request: Any) -> SandboxAccount:
    if request.config.getoption('--backend') == 'sandbox':
        return sandbox.get_accounts().pop()
    else:
        creator_private_key, creator_addr = generate_account()
        signer = AccountTransactionSigner(creator_private_key)
        return SandboxAccount(address=creator_addr, private_key=creator_private_key, signer=signer)


@pytest.fixture(scope='session')
def initial_state_fixture(request, algod, pyteal_code_module_str, creator_account) -> KCointVaultClient:
    pyteal_module = importlib.import_module(pyteal_code_module_str)

    if request.config.getoption('--backend') == 'kavm':
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr(
            target=algosdk.atomic_transaction_composer,
            name='AtomicTransactionComposer',
            value=KAVMAtomicTransactionComposer,
        )
        monkeypatch.setattr(
            target=beaker.client.application_client,
            name='AtomicTransactionComposer',
            value=KAVMAtomicTransactionComposer,
        )
    return KCointVaultClient(
        algod=algod,
        creator_account=creator_account,
        beaker_application=pyteal_module.KCoinVault(version=6, assemble_constants=False),
    )
