import logging
import sys
import pytest

from algosdk.account import generate_account
from kavm.algod import KAVMClient
from kcoin_vault.client import ContractClient


def interact(args=sys.argv) -> None:
    log_level = 'ERROR'
    if len(args) > 3:
        log_level = args[3]

    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(message)s',
        level=log_level,
        stream=sys.stdout,
    )

    pyteal_code_file = args[1]
    pyteal_code_module_str = pyteal_code_file.strip('.py').replace('/', '.')

    creator_private_key, creator_addr = generate_account()
    creator_addr = str(creator_addr)
    algod = KAVMClient(faucet_address=creator_addr, log_level=logging.DEBUG)
    client = ContractClient(
        algod, creator_addr, creator_private_key, pyteal_code_module_str
    )

    microalgos = int(args[2])
    minted = client.call_mint(creator_addr, creator_private_key, microalgos)
    print(f'mint({microalgos}) => {minted}')
    got_back = client.call_burn(creator_addr, creator_private_key, minted)
    print(f'burn({minted}) => {got_back}')


def run_prop_test(args=sys.argv) -> None:
    pyteal_code_file = args[1]
    pyteal_code_module_str = pyteal_code_file.strip('.py').replace('/', '.')

    testfilename = args[2]

    verbose = len(args) > 3 and args[3] == '--verbose'

    sys.exit(
        pytest.main(
            [
                "-s",
                "--tb=short",
                f"--hypothesis-verbosity={'verbose' if verbose else 'normal'}",
                "--hypothesis-show-statistics",
                "--pyteal-code-module-str",
                pyteal_code_module_str,
                testfilename,
            ]
        )
    )
