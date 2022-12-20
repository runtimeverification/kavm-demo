import logging
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Callable, Final, List, TypeVar

import coloredlogs
import pytest
from kavm.prover import AutoProver
from pyk.cli_utils import file_path

T = TypeVar('T')

_LOGGER: Final = logging.getLogger(__name__)
_LOG_FORMAT: Final = '%(levelname)s %(asctime)s %(name)s - %(message)s'


def run_demo(args=sys.argv) -> None:
    sys.setrecursionlimit(15000000)
    parser = create_argument_parser()
    args = parser.parse_args()
    coloredlogs.install(level=_loglevel(args), fmt=_LOG_FORMAT)

    if args.command == 'test':
        exec_test(
            pyteal_code_file=args.pyteal_code_file,
            test_code_file=args.test_code_file,
            verbose=args.verbose,
            backend=args.backend,
        )
    elif args.command == 'verify':
        exec_verify(
            pyteal_code_file=args.pyteal_code_file,
        )


def exec_test(
    pyteal_code_file: Path,
    test_code_file: Path,
    verbose: bool = False,
    backend: str = 'kavm',
) -> None:
    pyteal_code_module_str = str(pyteal_code_file).strip('.py').replace('/', '.')
    pytest.main(
            [
                "-s",
                "--tb=short",
                f"--hypothesis-verbosity={'verbose' if verbose else 'normal'}",
                "--hypothesis-show-statistics",
                f"--backend={backend}",
                "--pyteal-code-module-str",
                pyteal_code_module_str,
                str(test_code_file),
            ]
        )

def exec_verify(
    pyteal_code_file: Path,
) -> None:
    pyteal_code_module_str = str(pyteal_code_file).strip('.py').replace('/', '.')
    sys.setrecursionlimit(15000000)

    _LOGGER.info(f'Verifying specifications in module {pyteal_code_module_str}')

    prover = AutoProver(
        pyteal_module_name=pyteal_code_module_str,
        app_id=1,
        sdk_app_creator_account_dict=sdk_app_creator_account_dict,
        sdk_app_account_dict=sdk_app_account_dict,
    )
    prover.prove('mint')
    prover.prove('burn')


def create_argument_parser() -> ArgumentParser:
    def list_of(
        elem_type: Callable[[str], T], delim: str = ';'
    ) -> Callable[[str], List[T]]:
        def parse(s: str) -> List[T]:
            return [elem_type(elem) for elem in s.split(delim)]

        return parse

    parser = ArgumentParser(prog='kavm-demo')

    shared_args = ArgumentParser(add_help=False)
    shared_args.add_argument(
        '--verbose', '-v', default=False, action='store_true', help='Verbose output.'
    )
    shared_args.add_argument(
        '--debug', default=False, action='store_true', help='Debug output.'
    )
    shared_args.add_argument(
        '--profile',
        default=False,
        action='store_true',
        help='Coarse process-level profiling.',
    )
    shared_args.add_argument(
        '--pyteal-code-file',
        dest='pyteal_code_file',
        type=file_path,
        help='Path to the PyTeal source code file to test',
    )

    command_parser = parser.add_subparsers(
        dest='command', required=True, help='Command to execute'
    )

    # test
    test_subparser = command_parser.add_parser(
        'test',
        help='Run a property test',
        parents=[shared_args],
        allow_abbrev=False,
    )
    test_subparser.add_argument(
        '--backend',
        dest='backend',
        type=str,
        choices=['kavm', 'sandbox'],
        help='Interpreter to execute the tests with',
        default='kavm',
    )
    test_subparser.add_argument(
        '--test-code-file',
        dest='test_code_file',
        type=file_path,
        help='Path to the Python file with the testing code',
    )

    # verify
    test_subparser = command_parser.add_parser(
        'verify',
        help='Verify the pre and post conditions of contract methods',
        parents=[shared_args],
        allow_abbrev=False,
    )

    return parser


def _loglevel(args: Namespace) -> int:
    if args.debug:
        return logging.DEBUG

    if args.verbose or args.profile:
        return logging.INFO

    return logging.WARNING

sdk_app_creator_account_dict = {
    "address": "DJPACABYNRWAEXBYKT4WMGJO5CL7EYRENXCUSG2IOJNO44A4PWFAGLOLIA",
    "amount": 999999000000,
    "amount-without-pending-rewards": None,
    "apps-local-state": None,
    "apps-total-schema": None,
    "assets": [{"amount": 500000, "asset-id": 1, "is-frozen": False}],
    "created-apps": [
        {
            "id": 1,
            "params": {
                "creator": "DJPACABYNRWAEXBYKT4WMGJO5CL7EYRENXCUSG2IOJNO44A4PWFAGLOLIA",
                "approval-program": "approval.teal",
                "clear-state-program": "clear.teal",
                "local-state-schema": {"nbs": 0, "nui": 0},
                "global-state-schema": {"nbs": 0, "nui": 2},
                "global-state": [
                    {"key": "YXNzZXRfaWQ=", "value": {"bytes": "", "type": 2, "uint": 1}},
                    {"key": "ZXhjaGFuZ2VfcmF0ZQ==", "value": {"bytes": "", "type": 2, "uint": 2}},
                ],
            },
        }
    ],
    "created-assets": [],
    "participation": None,
    "pending-rewards": None,
    "reward-base": None,
    "rewards": None,
    "round": None,
    "status": None,
    "sig-type": None,
    "auth-addr": None,
}

sdk_app_account_dict = {
    "address": "WCS6TVPJRBSARHLN2326LRU5BYVJZUKI2VJ53CAWKYYHDE455ZGKANWMGM",
    "amount": 1000000,
    "amount-without-pending-rewards": None,
    "apps-local-state": None,
    "apps-total-schema": None,
    "assets": [{"amount": 500000, "asset-id": 1, "is-frozen": False}],
    "created-apps": [],
    "created-assets": [
        {
            "index": 1,
            "params": {
                "clawback": "WCS6TVPJRBSARHLN2326LRU5BYVJZUKI2VJ53CAWKYYHDE455ZGKANWMGM",
                "creator": "WCS6TVPJRBSARHLN2326LRU5BYVJZUKI2VJ53CAWKYYHDE455ZGKANWMGM",
                "decimals": 3,
                "default-frozen": False,
                "freeze": "WCS6TVPJRBSARHLN2326LRU5BYVJZUKI2VJ53CAWKYYHDE455ZGKANWMGM",
                "manager": "WCS6TVPJRBSARHLN2326LRU5BYVJZUKI2VJ53CAWKYYHDE455ZGKANWMGM",
                "metadata-hash": "",
                "name": "K Coin",
                "reserve": "WCS6TVPJRBSARHLN2326LRU5BYVJZUKI2VJ53CAWKYYHDE455ZGKANWMGM",
                "total": 1000000,
                "unit-name": "microK",
                "url": "",
            },
        }
    ],
    "participation": None,
    "pending-rewards": None,
    "reward-base": None,
    "rewards": None,
    "round": None,
    "status": None,
    "sig-type": None,
    "auth-addr": None,
}
