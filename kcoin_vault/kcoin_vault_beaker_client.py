import logging
from typing import Final
import pytest

import algosdk.atomic_transaction_composer
from algosdk.v2client.algod import AlgodClient
import beaker
from beaker.application import Application

from beaker.client.application_client import ApplicationClient
from beaker.sandbox.kmd import SandboxAccount
from beaker import consts

from algosdk.atomic_transaction_composer import AtomicTransactionComposer, TransactionWithSigner

# from algosdk.atomic_transaction_composer import TransactionWithSigner
from algosdk.future import transaction

from kavm.algod import KAVMAtomicTransactionComposer, KAVMClient

from kcoin_vault.kcoin_vault_beaker import KCoinVault

_LOGGER: Final = logging.getLogger(__name__)
_LOG_FORMAT: Final = '%(levelname)s %(asctime)s %(name)s - %(message)s'


class KCointVaultClient:
    '''
    The initializer sets up initial state for testing:
      * create the app
      * trigger creation of app's asset
      * creator opts into app's asset
    '''

    def __init__(
        self, algod: AlgodClient | KAVMClient, creator_account: SandboxAccount, beaker_application: Application
    ) -> None:

        self.creator_account = creator_account

        self.beaker_application = beaker_application
        self.beaker_client = ApplicationClient(client=algod, app=beaker_application, signer=creator_account.signer)

        self.sp = self.beaker_client.get_suggested_params()
        self.sp.flat_fee = True
        self.sp.fee = 2000
        self.algod = algod

        # create app
        self.app_id, app_addr, _ = self.beaker_client.create()
        _LOGGER.info(f'Deployed KCoinVault with app id {self.app_id} and address {app_addr}')

        # Fund app with algos
        self.beaker_client.fund(1 * consts.algo)

        # Initialize App's asset
        responce = self.beaker_client.call(method=KCoinVault.init_asset)
        self.asset_id = responce.return_value
        _LOGGER.info(f'Initialized KCoin with ASA id {self.asset_id}')

        # Opt-in to app's asset
        comp = AtomicTransactionComposer()
        comp.add_transaction(
            TransactionWithSigner(
                transaction.AssetOptInTxn(
                    sender=creator_account.address,
                    sp=self.sp,
                    index=self.asset_id,
                ),
                signer=creator_account.signer,
            )
        )
        comp.execute(self.algod, 2)

    def call_mint(
        self,
        sender_account: SandboxAccount,
        microalgo_amount: int,
    ) -> int:
        """
        Call app's 'mint' method
        """
        responce = self.beaker_client.call(
            method=KCoinVault.mint,
            foreign_assets=[self.asset_id],
            suggested_params=self.sp,
            payment=TransactionWithSigner(
                transaction.PaymentTxn(
                    sender=sender_account.address,
                    receiver=self.beaker_client.app_addr,
                    sp=self.sp,
                    amt=microalgo_amount,
                ),
                signer=sender_account.signer,
            ),
        )
        return responce.return_value

    def call_burn(
        self,
        sender_account: SandboxAccount,
        asset_amount: int,
    ) -> int:
        """
        Call app's 'burn' method
        """
        responce = self.beaker_client.call(
            method=KCoinVault.burn,
            foreign_assets=[self.asset_id],
            suggested_params=self.sp,
            asset_transfer=TransactionWithSigner(
                transaction.AssetTransferTxn(
                    sender=sender_account.address,
                    sp=self.sp,
                    index=self.asset_id,
                    receiver=self.beaker_client.app_addr,
                    amt=asset_amount,
                ),
                signer=sender_account.signer,
            ),
        )
        return responce.return_value
