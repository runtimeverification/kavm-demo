import logging
import json
import pytest


def test(initial_state_fixture):
    kcoin_client = initial_state_fixture
    acct1 = kcoin_client.creator_account

    print(f"App account info: {json.dumps(kcoin_client.beaker_client.get_application_account_info(), indent=4)}")
    print(f"Current app global state: {kcoin_client.beaker_client.get_application_state()}")

    microalgo_amount = 1000
    minted = kcoin_client.call_mint(sender_account=acct1, microalgo_amount=microalgo_amount)
    print(f'mint: {microalgo_amount} => {minted}')
    redeemed = kcoin_client.call_burn(sender_account=acct1, asset_amount=minted)
    print(f'burn: {minted} => {redeemed}')
