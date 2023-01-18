import logging
import sys
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Callable, Final, List, TypeVar
import importlib

import pyteal

import coloredlogs
import pytest
from kavm.prover import AutoProver
import kavm
from pyk.cli_utils import file_path

T = TypeVar('T')

_LOGGER: Final = logging.getLogger(__name__)
_LOG_FORMAT: Final = '%(levelname)s %(asctime)s %(name)s - %(message)s'


def run_demo(args=sys.argv) -> None:
    sys.setrecursionlimit(15000000)
    parser = create_argument_parser()
    args = parser.parse_args()
    coloredlogs.install(level=_loglevel(args), fmt=_LOG_FORMAT)

    if not args.debug:
        logging.getLogger('pyk.ktool.kprove').setLevel(logging.CRITICAL)
        logging.getLogger('pyk.ktool.krun').setLevel(logging.CRITICAL)

    if args.command == 'test':
        exec_test(
            pyteal_code_file=args.pyteal_code_file,
            test_code_file=args.test_code_file,
            verbose=args.verbose,
            backend=args.backend,
        )
    elif args.command == 'verify':
        exec_verify(pyteal_code_file=args.pyteal_code_file, method=args.method)
    elif args.command == 'simulate':
        exec_simulate(pyteal_code_file=args.pyteal_code_file, methods=args.methods, backend=args.backend)


def exec_test(
    pyteal_code_file: Path,
    test_code_file: Path,
    verbose: bool = False,
    backend: str = 'kavm',
) -> None:
    if not verbose:
        logging.getLogger('kavm.kavm').setLevel(logging.CRITICAL)
        logging.getLogger('kavm.algod').setLevel(logging.CRITICAL)
    pyteal_code_module_str = str(pyteal_code_file).strip('.py').replace('/', '.')
    pytest.main(
        [
            "-s",
            "--tb=no",
            f"--hypothesis-verbosity={'verbose' if verbose else 'normal'}",
            "--hypothesis-show-statistics",
            f"--backend={backend}",
            "--pyteal-code-module-str",
            pyteal_code_module_str,
            str(test_code_file),
        ]
    )


def exec_simulate(pyteal_code_file: Path, methods: str, backend: str = 'kavm', verbose: bool = False) -> None:
    if not verbose:
        logging.getLogger('kavm.kavm').setLevel(logging.CRITICAL)
        logging.getLogger('kavm.algod').setLevel(logging.CRITICAL)
    pyteal_code_module_str = str(pyteal_code_file).strip('.py').replace('/', '.')
    test_code_file = 'kcoin_vault/test_method_sequence.py'
    sys.exit(
        pytest.main(
            args=[
                "-s",
                f"--tb={'short' if verbose else 'no'}",
                "--disable-warnings",
                f"--backend={backend}",
                f"--pyteal-code-module-str={pyteal_code_module_str}",
                f"--methods={methods}",
                str(test_code_file),
            ]
        )
    )


def exec_verify(
    pyteal_code_file: Path,
    method: str,
) -> None:
    # monkey path the pyteal.Router class with pre-/post-conditions decorators
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            target=pyteal.Router,
            name='hoare_method',
            value=kavm.prover.router_hoare_method,
            raising=False,
        )
        monkeypatch.setattr(
            target=pyteal.Router,
            name='precondition',
            value=kavm.prover.router_precondition,
            raising=False,
        )
        monkeypatch.setattr(
            target=pyteal.Router,
            name='postcondition',
            value=kavm.prover.router_postcondition,
            raising=False,
        )

        pyteal_code_module_str = str(pyteal_code_file).strip('.py').replace('/', '.')
        pyteal_module = importlib.import_module(pyteal_code_module_str)
        sys.setrecursionlimit(15000000)

        _LOGGER.info(f'Verifying specifications in module {pyteal_code_module_str}')

        # Note that KAVM can use account data that is retrived from Algorand Node REST API.
        # We define the account data for the KCoin Vault contract and its creator at the
        # bottom of this file for portability.
        prover = AutoProver(
            # pyteal_module_name=pyteal_code_module_str,
            beaker_application=pyteal_module.KCoinVault(version=6, assemble_constants=False),
            app_id=1,
            sdk_app_creator_account_dict=sdk_app_creator_account_dict,
            sdk_app_account_dict=sdk_app_account_dict,
            method_names=[method],
        )
        prover.prove(method)


def create_argument_parser() -> ArgumentParser:
    def list_of(elem_type: Callable[[str], T], delim: str = ';') -> Callable[[str], List[T]]:
        def parse(s: str) -> List[T]:
            return [elem_type(elem) for elem in s.split(delim)]

        return parse

    parser = ArgumentParser(prog='kavm-demo')

    shared_args = ArgumentParser(add_help=False)
    shared_args.add_argument('--verbose', '-v', default=False, action='store_true', help='Verbose output.')
    shared_args.add_argument('--debug', default=False, action='store_true', help='Debug output.')
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
        required=True,
        help='Path to the PyTeal source code file to test',
    )

    command_parser = parser.add_subparsers(dest='command', required=True, help='Command to execute')

    # test
    test_subparser = command_parser.add_parser(
        'test',
        help='Run a concrete property test',
        parents=[shared_args],
        allow_abbrev=False,
    )
    test_subparser.add_argument(
        '--backend',
        dest='backend',
        type=str,
        choices=['kavm', 'sandbox'],
        help='Interpreter to execute the tests with, KAVM or the Algorand Sandbox',
        default='kavm',
    )
    test_subparser.add_argument(
        '--test-code-file',
        dest='test_code_file',
        type=file_path,
        help='Path to the Python file with the testing code',
    )

    # verify
    verify_subparser = command_parser.add_parser(
        'verify',
        help='Verify the pre and post conditions of contract methods by symbolic execution',
        parents=[shared_args],
        allow_abbrev=False,
    )
    verify_subparser.add_argument(
        '--method',
        dest='method',
        type=str,
        help='Method of the contract to verify',
    )

    # simulate
    simulate_subparser = command_parser.add_parser(
        'simulate',
        help='Run a simulation',
        parents=[shared_args],
        allow_abbrev=False,
    )
    simulate_subparser.add_argument(
        '--methods',
        dest='methods',
        type=str,
        required=True,
        help='Method sequence to call, for example \'mint(10000) burn(20000)\'',
    )
    simulate_subparser.add_argument(
        '--backend',
        dest='backend',
        type=str,
        choices=['kavm', 'sandbox'],
        help='Interpreter to execute the tests with',
        default='kavm',
    )

    return parser


def _loglevel(args: Namespace) -> int:
    if args.debug:
        return logging.DEBUG

    return logging.INFO


# Concrete data to bootstrap verification. Can also be retrieved from an Algorand Node via REST API
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
                    {"key": "ZXhjaGFuZ2VfcmF0ZQ==", "value": {"bytes": "", "type": 2, "uint": 2000}},
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
