import re
from typing import Any, List, Final
import logging

_LOGGER: Final = logging.getLogger(__name__)


def test_method_sequence(initial_state_fixture, methods: List[str]) -> None:
    re_mint_amount = re.compile(r'mint\(([0-9]*)\)')
    re_burn_amount = re.compile(r'burn\(([0-9]*)\)')
    kcoin_client, user_address, user_pk = initial_state_fixture
    _LOGGER.info(f'Running method sequence: {methods}')
    for method in methods:
        if method.startswith('mint'):
            amount = int(re_mint_amount.match(method).group(1))
            output = kcoin_client.call_mint(user_address, user_pk, amount)
            _LOGGER.info(f'{method} => {output}')
        elif method.startswith('burn'):
            amount = int(re_burn_amount.match(method).group(1))
            output = kcoin_client.call_burn(user_address, user_pk, amount)
            _LOGGER.info(f'{method} => {output}')
        else:
            raise RuntimeError(f'No such method {method}')
        assert output
