import base64
import importlib
import pytest

import pyteal
import algosdk
from algosdk.atomic_transaction_composer import AccountTransactionSigner, TransactionWithSigner
from algosdk.future import transaction
from kavm.algod import KAVMAtomicTransactionComposer, KAVMClient


def compile_teal(client, source_code):
    """Compile TEAL source code to binary for a transaction"""
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response["result"])


class ContractClient:
    '''
    The initializer sets up initial state for testing:
      * create the app
      * trigger creation of app's asset
      * creator opts into app's asset
    '''

    def __init__(
        self,
        algod,
        creator_addr,
        creator_private_key,
        pyteal_code_module,
    ) -> None:

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(
                target=pyteal.Router,
                name='hoare_method',
                value=lambda *args, **kwargs: lambda _: None,
                raising=False,
            )
            monkeypatch.setattr(
                target=pyteal.Router,
                name='precondition',
                value=lambda *args, **kwargs: lambda _: None,
                raising=False,
            )
            monkeypatch.setattr(
                target=pyteal.Router,
                name='postcondition',
                value=lambda *args, **kwargs: lambda _: None,
                raising=False,
            )
            config = importlib.import_module(pyteal_code_module)
            approval_source, clear_source, self.contract_interface = config.compile_to_teal()

        self.algod = algod
        # Compile approval and clear TEAL programs
        approval_program = compile_teal(algod, approval_source)
        clear_program = compile_teal(algod, clear_source)

        # create app
        on_complete = transaction.OnComplete.NoOpOC.real
        params = algod.suggested_params()

        global_schema = transaction.StateSchema(num_uints=2, num_byte_slices=0)
        txn = transaction.ApplicationCreateTxn(
            creator_addr, params, on_complete, approval_program, clear_program, global_schema, local_schema=None
        )

        signed_txn = txn.sign(creator_private_key)
        tx_id = signed_txn.transaction.get_txid()

        algod.send_transactions([signed_txn])
        transaction.wait_for_confirmation(algod, tx_id, 4)

        # display results
        transaction_response = algod.pending_transaction_info(tx_id)
        self.app_id = transaction_response["application-index"]

        ## Fund app with algos
        fund_app_account_txn = transaction.PaymentTxn(
            sender=creator_addr, sp=params, receiver=algosdk.logic.get_application_address(self.app_id), amt=10**6
        )
        signed_txn = fund_app_account_txn.sign(creator_private_key)
        tx_id = signed_txn.transaction.get_txid()
        algod.send_transactions([signed_txn])
        transaction.wait_for_confirmation(algod, tx_id, 4)

        # Initialize App's asset
        signer = AccountTransactionSigner(creator_private_key)
        comp = KAVMAtomicTransactionComposer()
        comp.add_method_call(
            self.app_id, self.contract_interface.get_method_by_name("init_asset"), creator_addr, params, signer
        )

        if isinstance(self.algod, KAVMClient):
            resp = comp.execute(self.algod, 2, override_tx_ids=['0'])
        else:
            resp = comp.execute(self.algod, 2)
        self.asset_id = resp.abi_results[0].return_value

        # Opt-in to app's asset
        comp = KAVMAtomicTransactionComposer()
        comp.add_transaction(
            TransactionWithSigner(
                transaction.AssetOptInTxn(sender=creator_addr, sp=params, index=self.asset_id), signer
            )
        )
        if isinstance(self.algod, KAVMClient):
            resp = comp.execute(self.algod, 2, override_tx_ids=['0'])
        else:
            resp = comp.execute(self.algod, 2)

    def call_mint(
        self,
        sender_addr: str,
        sender_pk: str,
        microalgo_amount: int,
    ) -> int:
        """
        Call app's 'mint' method
        """
        contract = self.contract_interface
        app_id = self.app_id
        asset_id = self.asset_id
        comp = KAVMAtomicTransactionComposer()
        signer = AccountTransactionSigner(sender_pk)
        sp = self.algod.suggested_params()
        sp.flat_fee = True
        sp.fee = 2000
        comp.add_method_call(
            app_id,
            contract.get_method_by_name('mint'),
            sender_addr,
            sp,
            signer,
            foreign_assets=[asset_id],
            method_args=[
                TransactionWithSigner(
                    transaction.PaymentTxn(
                        sender=sender_addr,
                        sp=sp,
                        receiver=algosdk.logic.get_application_address(app_id),
                        amt=microalgo_amount,
                    ),
                    signer,
                )
            ],
        )

        if isinstance(self.algod, KAVMClient):
            resp = comp.execute(self.algod, 2, override_tx_ids=['0', '1'])
        else:
            resp = comp.execute(self.algod, 2)
        return resp.abi_results[0].return_value

    def call_burn(
        self,
        sender_addr: str,
        sender_pk: str,
        asset_amount: int,
    ) -> int:
        """
        Call app's 'burn' method
        """
        contract = self.contract_interface
        app_id = self.app_id
        asset_id = self.asset_id
        comp = KAVMAtomicTransactionComposer()
        signer = AccountTransactionSigner(sender_pk)
        sp = self.algod.suggested_params()
        sp.flat_fee = True
        sp.fee = 2000
        comp.add_method_call(
            app_id,
            contract.get_method_by_name("burn"),
            sender_addr,
            sp,
            signer,
            foreign_assets=[asset_id],
            method_args=[
                TransactionWithSigner(
                    transaction.AssetTransferTxn(
                        sender=sender_addr,
                        sp=sp,
                        index=asset_id,
                        receiver=algosdk.logic.get_application_address(app_id),
                        amt=asset_amount,
                    ),
                    signer,
                )
            ],
        )
        if isinstance(self.algod, KAVMClient):
            resp = comp.execute(self.algod, 2, override_tx_ids=['0', '1'])
        else:
            resp = comp.execute(self.algod, 2)
        return resp.abi_results[0].return_value
