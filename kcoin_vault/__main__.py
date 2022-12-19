import logging
import sys
import pytest
from argparse import ArgumentParser, Namespace

from algosdk.account import generate_account
from algosdk.v2client.algod import AlgodClient

from kavm.algod import KAVMClient

from kcoin_vault.client import ContractClient
from kcoin_vault.sandbox import get_accounts


def interact(args=sys.argv) -> None:
    backend = 'kavm '
    if len(args) > 3:
        backend = args[3]

    log_level = 'ERROR'
    if len(args) > 4:
        log_level = args[4]

    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(message)s',
        level=log_level,
        stream=sys.stdout,
    )

    pyteal_code_file = args[1]
    pyteal_code_module_str = pyteal_code_file.strip('.py').replace('/', '.')

    if backend == 'kavm':
        creator_private_key, creator_addr = generate_account()
        creator_addr = str(creator_addr)
        algod = KAVMClient(faucet_address=creator_addr, log_level=logging.DEBUG)
    else:
        algod = AlgodClient("a" * 64, "http://localhost:4001")
        creator_addr, creator_private_key = get_accounts()[0]

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

    verbose = len(args) > 4 and args[4] == '--verbose'

    backend = 'kavm'
    if len(args) > 3:
        backend = args[3]

    sys.exit(
        pytest.main(
            [
                "-s",
                "--tb=short",
                f"--hypothesis-verbosity={'verbose' if verbose else 'normal'}",
                "--hypothesis-show-statistics",
                f"--backend={backend}",
                "--pyteal-code-module-str",
                pyteal_code_module_str,
                testfilename,
            ]
        )
    )

def create_argument_parser() -> ArgumentParser:
    def list_of(elem_type: Callable[[str], T], delim: str = ';') -> Callable[[str], List[T]]:
        def parse(s: str) -> List[T]:
            return [elem_type(elem) for elem in s.split(delim)]

        return parse

    parser = ArgumentParser(prog='kavm')

    shared_args = ArgumentParser(add_help=False)
    # shared_args.add_argument('--verbose', '-v', default=False, action='store_true', help='Verbose output.')
    shared_args.add_argument('--log-level', default=False, action='store_true', help='Debug output.')
    shared_args.add_argument('--profile', default=False, action='store_true', help='Coarse process-level profiling.')

    command_parser = parser.add_subparsers(dest='command', required=True, help='Command to execute')

    # test-property
    command_parser.add_parser(
        'test-property',
        help='Run a property test',
        parents=[shared_args],
        allow_abbrev=False,
    )

    # interact
    interact_subparser = command_parser.add_parser(
        'interact',
        help='Call mint and burn methods in sequence',
        parents=[shared_args],
        allow_abbrev=False,
    )
    interact_subparser.add_argument(
        '--definition-dir', dest='definition_dir', type=dir_path, help='Path to store the kompiled definition'
    )

    return parser
