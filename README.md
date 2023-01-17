## Automatic Formal Verification for Algorand Smart Contracts with KAVM

![verify-mint-optimized](https://user-images.githubusercontent.com/8296326/212864253-f19b29da-53ee-449e-9b47-09dde7f39ab2.gif)

KAVM leverages the [K Framework](https://kframework.org/) to provide automated formal verification for Algorand smart contracts. KAVM integrates with [`py-algorand-sdk`](https://py-algorand-sdk.readthedocs.io/en/latest/) and [PyTeal](https://pyteal.readthedocs.io/en/stable/). You can start using KAVM for verifying your contracts today!

Read on if you'd like to learn more!

### Install KAVM

The easiest way to install KAVM is provided by the `kup` tool. To install `kup`, run the following in your terminal:

```bash
bash <(curl https://kframework.org/install)
```

The installation script will guide you through a simple process that will also install Nix on your system. Once the previous command finishes, `kup` should be available in your shell. To verify the installation, execute:

```
kup list
```

The result should look similar to the following screenshot:

![1](https://user-images.githubusercontent.com/8296326/208937153-fa1f940a-d3ee-4588-905e-58b4d972fbec.png)


Naturally, KAVM uses the K Framework under the hood! Therefore we need to install the `k` package with `kup`:

```
kup install k
```

Once `kup` and the K Framework are installed, we can proceed to installing `kavm` itself:

```
kup install kavm
```

Finally, executing `kup list` should report that `kup`, `k` and `kavm` are installed:

![2](https://user-images.githubusercontent.com/8296326/208937184-36e8861f-dfa0-4709-b28d-1dcf185f5925.png)


### KAVM demo: catching rounding errors

Rounding errors in smart contracts can lead to severe security vulnerabilities and loss of funds. Rounding errors analysis is an important step we always perform in every smart contract audit that we do at Runtime Verification.

In this tutorial, we will look at an Algorand smart contract implemented in PyTeal, which implements a Vault for K Coins. Users can interact with the Vault to *mint* K Coins in exchange for their Algos and to *burn* their K Coins to redeem the Algos. We will use KAVM to *formally verify* that the `mint` and `burn` methods of the KCoint Vault work as expected.

#### Getting the demo source code

We have packaged the contract's source code into a tiny Python package. The package sets up the Python environment with the `poetry` tool. In case you do not have `poetry` installed, you can run the official [installer script](https://python-poetry.org/docs/#installation) like this:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Once `poetry` is set-up, clone the `kavm-demo` repository and change into it:

```bash
git clone https://github.com/runtimeverification/kavm-demo.git
cd kavm-demo
poetry install
```

Finally, KAVM needs some environment variables to access the `kup` installed K semantics. Temporarily add them to your shell like this:

```
export $(kavm env)
```

#### The K Coin Vault contract

The contract uses the PyTeal `Router` abstraction to define the [ABI](https://pyteal.readthedocs.io/en/stable/abi.html) of the contract, and plug the methods' implementations into it. KAVM integrates with PyTeal and `py-algorant-sdk`, and provides additional capabilities that allow decorating PyTeal router methods with *preconditions* and *postconditions*. Preconditions specify the *assumptions* about a method's arguments, and postconditions *assert* what the method's output must be. Let us have a look at the interface of the contract, with the implementation of the methods stripped down (full code available [here](https://github.com/runtimeverification/kavm-demo)):

```python
router = Router(
    name="K Coin Vault",
    bare_calls=BareCallActions(
        no_op=OnCompleteAction.create_only(Approve()),
        update_application=OnCompleteAction.never(),
        delete_application=OnCompleteAction.never(),
        clear_state=OnCompleteAction.never(),
    ),
)


@router.method
def init_asset(*, output: abi.Uint64) -> Expr:
    """
    Create the K Coin asset
    Can only be executed by the contract's creator
    Returns: created asset id
    """
    pass

@router.method
# ASSUME the payment amount is greater or equal to 100000
@router.precondition(expr='payment.get().amount() >= Int(10000)')
# ASSUME the payment amount is less or equal to 20000
@router.precondition(expr='payment.get().amount() <= Int(20000)')
# VERIFY THAT the output of the method is the expected minted amount of micro K coins
@router.postcondition(expr=f'output.get() == payment.get().amount() * Int({INITIAL_EXCHANGE_RATE}) / Int({SCALING_FACTOR})')
@router.hoare_method
def mint(payment: abi.PaymentTransaction, *, output: abi.Uint64) -> Expr:
    """
    Mint K Coins, issuing an inner asset transfer transaction to sender if successful
    Args:
        payment: A payment transaction containing the amount of Algos the user wishes to mint with.
            The receiver of this transaction must be this app's escrow account.
    Returns: minted amount of K Coins that the user gets
    """
    pass

# ASSUME the asset transfer amount is greater or equal to 100000
@router.precondition(expr='asset_transfer.get().amount() >= Int(10000)')
# ASSUME the asset transfer amount is less or equal to 20000
@router.precondition(expr='asset_transfer.get().amount() <= Int(20000)')
# VERIFY THAT the output of the method is the expected amount of microalgos
@router.postcondition(expr=f'output.get() == asset_transfer.get().amount() * Int({SCALING_FACTOR}) / Int({INITIAL_EXCHANGE_RATE})')
@router.hoare_method
@router.method
def burn(asset_transfer: abi.AssetTransferTransaction, *, output: abi.Uint64) -> Expr:
    """
    Burn K Coins, issuing an inner payment transaction to sender if successful
    Args:
        asset_transfer: An asset transfer transaction containing the amount of K Coins (in microKs) the user wishes to burn.
            The receiver of this transaction must be this app's escrow account.
    Returns: amount of microalgos the users gets
    """
    pass
```

The contract has three ABI methods (Python functions marked with the `@router.method` decorator) for the two user-actions (mint and burn) and the single admin-action (init_asset). Besides the ABI methods, the contract accepts only one [*bare call*](https://pyteal.readthedocs.io/en/stable/abi.html#creating-an-arc-4-program), which facilitates application deployment (creation of the application in the Algorand blockchain). All other bare calls, such as application code update, deletion and clear state are rejected.

KAVM adds three additional decorators to PyTeal's `Router` class, in addition to the standard `@router.method`. The `@router.hoare_method` specifies that this method is compatible with KAVM's [Hoare logic](https://en.wikipedia.org/wiki/Hoare_logic)-based automated prover. The `@router.precondition` decorator specifies the assumptions we place on the method's arguments, while the `@router.postcondition` asserts the result.

Enough talking! Let's get our hand dirty and verify the specification!

#### Running the KAVM prover

Again, the specification of the `mint` method says that, under certain assumptions, the method should succeed and return the minted amount.
Let's see what KAVM thinks about the spec:

```
poetry run kavm-demo verify --verbose --pyteal-code-file kcoin_vault/kcoin_vault_pyteal.py \
  --method mint
```
![verify-mint-optimized](https://user-images.githubusercontent.com/8296326/212864253-f19b29da-53ee-449e-9b47-09dde7f39ab2.gif)

It looks like the prover is happy with the `mint` method and its spec! But what about `burn`? Let's see:

```
poetry run kavm-demo verify --verbose --pyteal-code-file kcoin_vault/kcoin_vault_pyteal.py \
  --method burn
```

Hmm, the prover is unhappy this time:

![verify-burn-final](https://user-images.githubusercontent.com/8296326/208942585-0f453a43-e07b-4be3-a1b2-89d7b95d15e9.gif)

We see a message that something went wrong with the `burn` method and a bunch of scary-looking expressions. Let's try to make sense of them.

The first question we should ask is: "where are the variables from the spec?". Remember, that the spec we wanted the prover to verify was accessing the `asset_transfer.get().amount()` value, the asset transfer amount. Inside KAVM, this value becomes *symbolic* and gets the name `ASSET_TRANSFER_AMOUNT` of sort `Int`. Anyway, where are the `precondition`s? We wanted the amount to be between 10000 and 20000, did the prover even consider our spec? Let's sort the thing out a bit. Here's the table that translates the Matching Logic constraints into more familiar PyTeal expressions:


|   | Matching Logic                                                                              | PyTeal                                                                    |
|:--|:--------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------|
| 1 | `true #Equals 20000 >=Int ASSET_TRANSFER_AMOUNT:Int`                                        | `20000 >= asset_transfer.get().amount()`                                  |
| 2 | `true #Equals 500000 -Int ASSET_TRANSFER_AMOUNT:Int >=Int 0`                                | `50000 - asset_transfer.get().amount() >= 0`                              |
| 3 | `true #Equals 1000000 -Int ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000 >=Int 100000`      | `100000 - asset_transfer.get().amount() / 2000 * 1000 >= 100000`          |
| 4 | `true #Equals 18446744073709551615 >=Int ASSET_TRANSFER_AMOUNT:Int`                         | `MAX_UINT64 >= asset_transfer.get().amount()`                             |
| 5 | `true #Equals 18446744073709551615 >=Int ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000`     | `MAX_UINT64 >= asset_transfer.get().amount() / 2000 * 1000`               |
| 6 | `true #Equals ASSET_TRANSFER_AMOUNT:Int +Int 500000 >=Int 0`                                | `asset_transfer.get().amount() + 50000 >= 0`                              |
| 7 | `true #Equals ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000 +Int 999999000000 >=Int 100000` | `asset_transfer.get().amount() / 2000 * 1000 +Int 999999000000 >= 100000` |
| 8 | `true #Equals ASSET_TRANSFER_AMOUNT:Int >=Int 0`                                            | `asset_transfer.get().amount() >= 0`                                      |
| 9 | `true #Equals ASSET_TRANSFER_AMOUNT:Int >=Int 10000`                                        | `asset_transfer.get().amount() >= 10000`                                  |


The first and the last row in the table above correspond to the preconditions that we've put onto the `asset_transfer` amount. What are the other expressions? They are called side-conditions, or path-conditions --- and are inserted by KAVM during symbolic execution. In a nutshell, these conditions represent the symbolic path that KAVM has followed through the contract's code while executing the `burn` method.

Note that we have intentionally omitted the last expression from the table, which describes the `output`, i.e. the result of the contract. We will soon see that it's the symbolic form of the output that has caused the proof to fail. But first, let's take a break form all this symbolic stuff!

### Symbolic execution? Matching logic?? Just give me counterexamples!

Have you ever been feeling intimidated by formal verification? We have! That's why we want to make it *understandable*! And what's easier to understand than concrete examples?

KAVM is also capable of concrete execution. Effectively, KAVM can act as the Algorand Sandbox, by integrating K's concrete execution backend with `py-algorand-sdk`. For this demo, we have created a simple `pytest`-based tester that allows executing sequences of methods. For example, let's try a simple example that replicates the failing proof:

```
poetry run kavm-demo simulate --pyteal-code-file kcoin_vault/kcoin_vault_pyteal.py \
  --methods 'mint(10000) burn(20000)' --backend kavm --verbose
```

Hmm, looks like the test has passed:

```
INFO 2022-12-21 13:47:23 kcoin_vault.test_method_sequence - Running method sequence: ['mint(10000)', 'burn(20000)']
INFO 2022-12-21 13:47:24 kcoin_vault.test_method_sequence - mint(10000) => 20000
INFO 2022-12-21 13:47:24 kcoin_vault.test_method_sequence - burn(20000) => 10000
.

============================= 1 passed, 7 warnings in 5.46s =============================
```

How come?? The proof has been failing with these constraints. Well, the thing is that the error is much sneakier than one might expect! Let's try another example, with a smaller amount to burn:

```
poetry run kavm-demo simulate --pyteal-code-file kcoin_vault/kcoin_vault_pyteal.py \
  --methods 'mint(10000) burn(999)' --backend kavm --verbose
```

```
kcoin_vault.test_method_sequence - Running method sequence: ['mint(10000)', 'burn(999)']
INFO 2022-12-21 13:50:10 kcoin_vault.test_method_sequence - mint(10000) => 20000
INFO 2022-12-21 13:50:11 kcoin_vault.test_method_sequence - burn(999) => 0
F

================================ short test summary info ================================
FAILED kcoin_vault/test_method_sequence.py::test_method - assert 0
============================= 1 failed, 7 warnings in 5.52s =============================
```

Aha! So, burning 999 micro K coins produces 0 microalgos... that doesn't seem right. There must be an error in the exchange logic.

It turns out, KAVM has already reported this error, and that's why the verification of the `burn` method has been failing, even though we've constrained the amount to burn to be much larger than 999. Let's have a look at the verification constraints again, and strip down the unnecessary details:

```
 #Not ({
   b"\x15\x1f|u" +Bytes padLeftBytes ( Int2Bytes ( log2Int (
     ASSET_TRANSFER_AMOUNT:Int *Int 1000 /Int 2000
     ) +Int 8 /Int 8 , ASSET_TRANSFER_AMOUNT:Int *Int 1000 /Int 2000 , BE ) , 8 , 0 )
   #Equals
   b"\x15\x1f|u" +Bytes padLeftBytes ( Int2Bytes ( log2Int (
     ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000
     ) +Int 8 /Int 8 , ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000 , BE ) , 8 , 0 )
   } )

=> {rewrite in PyTeal} =>

ASSET_TRANSFER_AMOUNT:Int *Int 1000 /Int 2000 != ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000
```

The constraint, in its Matching Logic form, looks rather terrible, but it boils down to a simple inequality of the form `X * Y / Z != X / Z * Y`. But how come these are different? They are, because Algorand smart contracts (well, any smart contracts, really) operate with fixed-point numbers, rather than with floating-point numbers, i.e. the `/` operation in PyTeal is, in fact, integer division.

So, where does the error come from? Let's look at the PyTeal subroutine that converts micro K coins to microalgos, which is used internally by the `burn` method's implementation:

```python
@Subroutine(TealType.uint64)
def kcoin_to_algos(asset_amount: Expr) -> Expr:
    """
    Convert microKs to microalgos

    microAlgos = microKs * SCALING_FACTOR / EXCHANGE_RATE
    """
    return Mul(Div(asset_amount, App.globalGet(Bytes("exchange_rate"))), Int(SCALING_FACTOR))
```

When we look at the PyTeal `Expr` that this function builds, we see that the order of operations is indeed wrong! We first divide by the exchange rate and only then multiply by the scaling factor. If the value of `asset_amount` is smaller than the `"exchange_rate"` global variable, the expression will evaluate to zero, and the user funds will be lost!

KAVM has managed to catch this error because the *symbolic* expression representing the `output` of the `burn` method was different from the postcondition that we specified:

```
@router.postcondition(
    expr=f'output.get() == asset_transfer.get().amount() * Int({SCALING_FACTOR}) / Int({INITIAL_EXCHANGE_RATE})'
    )
```

Indeed, the postcondition has the right order of operations: scale the value up first, and then divide by the exchange rate. That's how symbolic execution can find subtle errors that can lead to loss of user and/or contract funds.

#### Fixing the code and verifying

The corrected implementation of the K Coin Vault contract can be found in `kcoin_vault/kcoin_vault_pyteal_fixed.py`. We can verify it with the following two commands:

```
poetry run kavm-demo verify --verbose \
    --pyteal-code-file kcoin_vault/kcoin_vault_pyteal_fixed.py --method mint
poetry run kavm-demo verify --verbose \
    --pyteal-code-file kcoin_vault/kcoin_vault_pyteal_fixed.py --method burn
```

The prover should now report success for both methods!

### What's next

We hope this small demo has persuaded you that the Algorand ecosystem now has a formal verification tool! While the user interface is somewhat limited now, we're working very hard to scale it up and integrate seamlessly into the existing tooling. Try [KAVM](https://github.com/runtimeverification/avm-semantics/) today, it's free and open source!

#### Integration with Algorand Beaker

The [Beaker](https://developer.algorand.org/articles/hello-beaker/) is an Algorand smart contract development framework that makes designing, testing, and deploying PyTeal smart contracts much easier. Since Beaker leverages `py-algorand-sdk` to interact with an Algorand node or sandbox, it will be able to use KAVM as a backend too. Yes, with Beaker we'd be able to use KAVM as a drop-in replacement for the Algorand Sandbox, thus making it trivial to bring formal verification, to any Beaker-powered project.

#### Support for global and local state in specifications

So far KAVM's `AutoProver` only allows placing pre- and postconditions on methods' arguments and output. A natural next step would be to allow specifying the form for global state, local state and box storage. While this is available to users experienced with K, the Python interface will be augmented with this ability soon.

### Concluding remarks

KAVM is developed by [Runtime Verification](https://runtimeverification.com/) with support from the Algorand Foundation.

At Runtime Verification, we are committed to smart contract security and we would like to make formal verification accessible to every developer!
