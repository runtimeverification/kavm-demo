from typing import Tuple

import pytest
from algosdk.abi import Contract
from algosdk.v2client.algod import AlgodClient

from kavm_demo.client import initial_state


@pytest.fixture(scope='session')
def initial_state_fixture() -> Tuple[AlgodClient, Contract, int, str, str, int]:
    return initial_state()
