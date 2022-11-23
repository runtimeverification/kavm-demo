import logging
import sys
import pytest

from algosdk.account import generate_account
from kavm.algod import KAVMClient
from kcoin_vault.client import ContractClient


def interact() -> None:
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.ERROR, stream=sys.stdout)

    creator_private_key, creator_addr = generate_account()
    creator_addr = str(creator_addr)
    algod = KAVMClient(faucet_address=creator_addr, log_level=logging.DEBUG)
    client = ContractClient(algod, creator_addr, creator_private_key)

    microalgos = 100
    minted = client.call_mint(creator_addr, creator_private_key, microalgos)
    got_back = client.call_burn(creator_addr, creator_private_key, minted)
    assert abs(got_back - microalgos) <= 1


def run_prop_test(args=sys.argv) -> None:
    testfilename = args[1]
    sys.exit(pytest.main(["--tb=short", "--hypothesis-show-statistics", testfilename]))
