from datetime import timedelta

from hypothesis import Phase, given, settings
from hypothesis import strategies as st

from kavm_demo.client import call_burn, call_mint

MIN_ARG_VALUE = 10
MAX_ARG_VALUE = 1 * 10**6


@settings(deadline=(timedelta(seconds=2)), max_examples=25, phases=[Phase.generate])
@given(
    microalgos=st.integers(min_value=MIN_ARG_VALUE, max_value=MAX_ARG_VALUE),
)
def test_contract(initial_state_fixture, microalgos: int) -> None:
    client, contract, app_id, creator_addr, creator_private_key, asset_id = initial_state_fixture
    minted = call_mint(client, contract, app_id, creator_addr, creator_private_key, asset_id, microalgos)
    got_back = call_burn(client, contract, app_id, creator_addr, creator_private_key, asset_id, minted)
    # assert abs(got_back - microalgos) <= 1
    assert got_back == microalgos

