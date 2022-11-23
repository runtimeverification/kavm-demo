import logging
import sys

import pytest

from kavm_demo.client import call_burn, call_mint, initial_state


def interact() -> None:
    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=logging.ERROR, stream=sys.stdout)

    client, contract, app_id, creator_addr, creator_private_key, asset_id = initial_state()

    microalgos = 100
    minted = call_mint(client, contract, app_id, creator_addr, creator_private_key, asset_id, microalgos)
    print(f"Calling 'mint' with {microalgos} microalgos => {minted}")
    got_back = call_burn(client, contract, app_id, creator_addr, creator_private_key, asset_id, minted)
    print(f"Calling 'burn' with {minted} items => {got_back} microalgos")


def run_prop_test(args=sys.argv) -> None:
    testfilename = args[1]
    sys.exit(pytest.main(["--tb=short", "--hypothesis-show-statistics", testfilename]))
