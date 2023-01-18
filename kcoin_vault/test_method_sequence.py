import re
from argparse import ArgumentError
from typing import Any, List, Final
import logging

_LOGGER: Final = logging.getLogger(__name__)
_LOG_FORMAT: Final = '%(levelname)s %(asctime)s %(name)s - %(message)s'


def test_method(request: Any, initial_state_fixture, methods: List[str]) -> None:
    re_mint_amount = re.compile(r'mint\(([0-9]*)\)')
    re_burn_amount = re.compile(r'burn\(([0-9]*)\)')
    kcoin_client = initial_state_fixture
    user_account = kcoin_client.creator_account
    _LOGGER.info(f'Running method sequence: {methods}')
    for method in methods:
        if method.startswith('mint'):
            amount = int(re_mint_amount.match(method).group(1))
            output = kcoin_client.call_mint(user_account, amount)
            _LOGGER.info(f'{method} => {output}')
        elif method.startswith('burn'):
            amount = int(re_burn_amount.match(method).group(1))
            output = kcoin_client.call_burn(user_account, amount)
            _LOGGER.info(f'{method} => {output}')
        else:
            raise RuntimeError(f'No such method {method}')
        assert output
