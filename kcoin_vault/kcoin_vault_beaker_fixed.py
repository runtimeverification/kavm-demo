from typing import Tuple, Final

from algosdk.abi import Contract
from pyteal import (
    App,
    Assert,
    Bytes,
    Div,
    Expr,
    Global,
    InnerTxn,
    InnerTxnBuilder,
    Int,
    Mul,
    Seq,
    TealType,
    Txn,
    TxnField,
    TxnType,
    abi,
)
from beaker.application import Application
from beaker.state import ApplicationStateValue
from beaker.decorators import create, external, internal

ASSET_TOTAL = 1000000000
ASSET_DECIMALS = 3
INITIAL_EXCHANGE_RATE = 2000
SCALING_FACTOR = 1000


class KCoinVault(Application):
    asset_id: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="K Coin ASA ID, created by the Vault",
    )
    exchange_rate: Final[ApplicationStateValue] = ApplicationStateValue(
        stack_type=TealType.uint64,
        descr="Exchnage rate of K Coin and Algo",
    )

    @create
    def create(self):
        return self.initialize_application_state()

    @external
    def init_asset(self, *, output: abi.Uint64) -> Expr:
        """
        Create the K Coin asset

        Can only be executed by the contract's creator

        Returns: created asset id

        """
        return Seq(
            Assert(Txn.sender() == Global.creator_address()),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetConfig,
                    TxnField.config_asset_total: Int(ASSET_TOTAL),
                    TxnField.config_asset_decimals: Int(ASSET_DECIMALS),
                    TxnField.config_asset_manager: Global.current_application_address(),
                    TxnField.config_asset_reserve: Global.current_application_address(),
                    TxnField.config_asset_freeze: Global.current_application_address(),
                    TxnField.config_asset_clawback: Global.current_application_address(),
                    TxnField.config_asset_name: Bytes("K Coin"),
                    TxnField.config_asset_unit_name: Bytes("microK"),
                }
            ),
            InnerTxnBuilder.Submit(),
            # App.globalPut(Bytes("asset_id"), InnerTxn.created_asset_id()),
            self.asset_id.set(InnerTxn.created_asset_id()),
            # App.globalPut(Bytes("exchange_rate"), Int(INITIAL_EXCHANGE_RATE)),
            self.exchange_rate.set(Int(INITIAL_EXCHANGE_RATE)),
            output.set(InnerTxn.created_asset_id()),
        )

    @internal(TealType.uint64)
    def algos_to_kcoin(self, algo_amount: Expr) -> Expr:
        """
        Convert microalgos to microKs:

        microKs = microAlgos * EXCHANGE_RATE / SCALING_FACTOR
        """
        return Div(Mul(algo_amount, App.globalGet(Bytes("exchange_rate"))), Int(SCALING_FACTOR))

    @internal(TealType.uint64)
    def kcoin_to_algos(self, asset_amount: Expr) -> Expr:
        """
        Convert microKs to microalgos

        microAlgos = microKs * SCALING_FACTOR / EXCHANGE_RATE
        """
        return Div(Mul(asset_amount, Int(SCALING_FACTOR)), App.globalGet(Bytes("exchange_rate")))

    @external
    def mint(self, payment: abi.PaymentTransaction, *, output: abi.Uint64) -> Expr:
        """
        Mint K Coins, issuing an inner asset transfer transaction to sender if successful

        Args:
            payment: A payment transaction containing the amount of Algos the user wishes to mint with.
                The receiver of this transaction must be this app's escrow account.

        Returns: minted amount of K Coins that the user gets
        """
        amount_to_mint = self.algos_to_kcoin(payment.get().amount())
        asset_id = App.globalGet(Bytes("asset_id"))
        return Seq(
            Assert(payment.get().receiver() == Global.current_application_address()),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.AssetTransfer,
                    TxnField.xfer_asset: asset_id,
                    TxnField.asset_receiver: Txn.sender(),
                    TxnField.asset_amount: amount_to_mint,
                    TxnField.fee: Int(0),
                }
            ),
            InnerTxnBuilder.Submit(),
            output.set(amount_to_mint),
        )

    @external
    def burn(self, asset_transfer: abi.AssetTransferTransaction, *, output: abi.Uint64) -> Expr:
        """
        Burn K Coins, issuing an inner payment transaction to sender if successful

        Args:
            asset_transfer: An asset transfer transaction containing the amount of K Coins (in microKs) the user wishes to burn.
                The receiver of this transaction must be this app's escrow account.

        Returns: amount of microalgos the users gets
        """
        microalgos_output = self.kcoin_to_algos(asset_transfer.get().asset_amount())
        return Seq(
            Assert(asset_transfer.get().asset_receiver() == Global.current_application_address()),
            InnerTxnBuilder.Begin(),
            InnerTxnBuilder.SetFields(
                {
                    TxnField.type_enum: TxnType.Payment,
                    TxnField.receiver: Txn.sender(),
                    TxnField.amount: microalgos_output,
                    TxnField.fee: Int(0),
                }
            ),
            InnerTxnBuilder.Submit(),
            output.set(microalgos_output),
        )
