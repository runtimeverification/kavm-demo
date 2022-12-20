## Automatic Formal Verification for Algorand Smart Contracts with KAVM

KAVM leverages [K Framework](https://kframework.org/) to provide fast property-testing and formal verification for Algorand smart contracts.

Here's KAVM in action:

![kavm-demo](https://user-images.githubusercontent.com/8296326/203607413-057cc6a5-d11b-4055-b332-63da26e15745.gif)

KAVM integrates with [`py-algorand-sdk`](https://py-algorand-sdk.readthedocs.io/en/latest/) and [PyTeal](https://pyteal.readthedocs.io/en/stable/). You can start using KAVM for testing your contracts today!

Read on if you'd like to learn more!

### How to install KAVM

#### Install `kup` tool

The easiest way to install KAVM is provided by the `kup` tool. To install `kup`, run the following in your terminal:

```bash
bash <(curl https://kframework.org/install)
```

The installation script will guide you through a simple process that will also install Nix on your system. Once the previous command finishes, which may take some time, `kup` should be available in your shell. To verify the installation, execute:

```
kup list
```

The result should look similar to the following screenshot:

![1](https://user-images.githubusercontent.com/8296326/202644795-897cf3d7-0a7c-4654-8998-4fc838ec632e.png)

Once `kup` is installed, we can proceed to installing `kavm` itself.

#### Install KAVM

**TEMPORARY**

Install KAVM from the specified Git revision (no binary cache unfortunately):

```
kup install kevm --version integrate-autoprover-2
```

<!-- In the screenshot above, we see kup reporting that the `kavm` package is available for installation. Proceed by typing `kup install kavm` to install it: -->

![2](https://user-images.githubusercontent.com/8296326/202645178-324a8bd2-cd8e-4eee-920d-6b4c65dd1241.png)

### KAVM demo: catching rounding errors

Rounding errors in smart contracts can lead to severe security vulnerabilities and loss of funds. Rounding errors analysis is an important step are always perform in every smart contract audit that we do at Runtime Verification.

In this tutorial, we will look at an Algorand smart contract implemented in PyTeal, which implements a Vault for K Coins. Users can interact with the Vault to *mint* K Coins in exchange for their Algos and to *burn* their K Coins to redeem the Algos. We will use KAVM to *formally verify* that the `mint` and `burn` methods of the KCoint Vault work as expected.

#### Getting the demo source code

We have packaged the contract's source code into a tiny Python package. The package sets-up the Python environment with the `poetry` tool. In case you do not have `poetry` installed, you can run the official [installer script](https://python-poetry.org/docs/#installation) like this:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Once `poetry` is set-up, clone the `kavm-demo` repository and change into it:

```bash
git clone https://github.com/runtimeverification/kavm-demo.git
cd kavm-demo
poetry install
```

Finally, KAVM needs some environment variables to access the `kup` installed K semantics. Temporary add them to your shell like this:

```
export $(kavm env)
```

#### The K Coin Vault contract

The contract uses the PyTeal `Router` abstraction to define the [ABI](https://pyteal.readthedocs.io/en/stable/abi.html) of the contract, and plug the methods implementations into it. KAVM integrates with PyTeal and `py-algorant-sdk`, and provides additional capabilities that allow decorating PyTeal router methods with pre-conditions and post-conditions. Pre-conditions specify the assumptions about method's arguments, and post-conditions assert what the method's output must be. Let us have a look at the interface of the contract, with the implementation of the methods stripped down (full code available [here](https://github.com/runtimeverification/kavm-demo)):

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
@router.precondition(expr='payment.get().amount() >= Int(10000)')
@router.precondition(expr='payment.get().amount() <= Int(20000)')
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

@router.precondition(expr='asset_transfer.get().amount() >= Int(10000)')
@router.precondition(expr='asset_transfer.get().amount() <= Int(20000)')
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

The contract has three ABI methods (Python functions marked with the `@router.method` decorator) for the two user-actions (mint and burn) and the single admin-action (init_asset). Besides the ABI methods, the contract accepts only one [*bare call*](https://pyteal.readthedocs.io/en/stable/abi.html#creating-an-arc-4-program), which facilitate application deployment (creation of the application in the Algorand blockchain). All other bare calls, such as application code update, deletion and clear state are rejected.

KAVM adds three addition decorators to PyTeal's `Router` class, in addition to the standard `@router.method`. The `@router.hoare_method` specifies that this method is compatible with KAVM's [Hoare logic](https://en.wikipedia.org/wiki/Hoare_logic)-based automated prover. The `@router.precondition` decorator specifies the the *assumtions* we place on the method's arguments, while the `@router.postcondition` asserts the result.

<!-- To test PyTeal contracts, the developers have to *deploy* them, since the source code above cannot be executed directly. The usual deployment workflow is to compile the contract's source code to TEAL, the executable language of the Algorand blockchain, and submit an application call transaction to an Algorand node that will create the contract. Interaction with the created contract is then done by submitting more application call transactions. -->

<!-- KAVM works a little differently. KAVM is not an implementation of the Algorand node, but rather a simulation and formal verification tool for Algorand smart contracts. Therefore, KAVM runs locally on the developer's machine, almost like the Algorand [Sandbox](https://github.com/algorand/sandbox). However, in contracts to the Sandbox, there is no HTTP communication involved when interacting with KAVM, therefore the gap between the Python testing/deployment script and the execution engine is much narrower. -->

<!-- With all that being said, we do not want the developers to think too much about the implementation details! Thus, we have designed KAVM to integrate well with `py-algorand-sdk`, making it possible to interact with KAVM almost as if it were, in fact, and Algorand node. -->

Enough talking! Let's get our hand dirty and verify the specification!

#### Running the KAVM prover

The specification of the 'mint' method says that, under certain assumptions, the method should succeed and return the minted amount.
Let's look one more time at the spec one more time, supplemented with comments:

```python
// ASSUME the payment amount is greater or equal to 100000
@router.precondition(expr='payment.get().amount() >= Int(10000)')
// ASSUME the payment amount is less or equal to 20000
@router.precondition(expr='payment.get().amount() <= Int(20000)')
// VERIFY THAT the output of the method is the expected minted amount of micro K coins
@router.postcondition(expr=f'output.get() == payment.get().amount() * Int({INITIAL_EXCHANGE_RATE}) / Int({SCALING_FACTOR})')
@router.hoare_method
def mint(payment: abi.PaymentTransaction, *, output: abi.Uint64) -> Expr:
    ...
```

Let's see what KAVM thinks about the spec by verifying the 'mint' method of the contract:

```
poetry run kavm-demo verify --verbose --pyteal-code-file kcoin_vault/kcoin_vault_pyteal.py --method mint
```

**TODO**: GIF for the successful mint

It looks like the prover is happy with the `mint` method and its spec! But what about `burn`? Let's see the commented spec:

```python
// ASSUME the asset transfer amount is greater or equal to 100000
@router.precondition(expr='asset_transfer.get().amount() >= Int(10000)')
// ASSUME the asset transfer amount is less or equal to 20000
@router.precondition(expr='asset_transfer.get().amount() <= Int(20000)')
// VERIFY THAT the output of the method is the expected amount of microalgos
@router.postcondition(expr=f'output.get() == asset_transfer.get().amount() * Int({SCALING_FACTOR}) / Int({INITIAL_EXCHANGE_RATE})')
@router.hoare_method
@router.method
def burn(asset_transfer: abi.AssetTransferTransaction, *, output: abi.Uint64) -> Expr:
```

and verify it:

```
poetry run kavm-demo verify --verbose --pyteal-code-file kcoin_vault/kcoin_vault_pyteal.py --method burn
```

Hmm, the prover is unhappy this time:

**TODO**: GIF for the failing burn

```
ERROR 2022-12-20 18:08:25 kavm.prover - Failed to verifiy specifiction for method: K-Coin-Vault-burn
INFO 2022-12-20 18:08:25 kavm.prover - KAVM <returnstatus>: """"
INFO 2022-12-20 18:08:25 kavm.prover - Constraints:
 #Not ( { b"\x15\x1f|u" +Bytes padLeftBytes ( Int2Bytes ( log2Int ( ASSET_TRANSFER_AMOUNT:Int *Int 1000 /Int 2000 ) +Int 8 /Int 8 , ASSET_TRANSFER_AMOUNT:Int *Int 1000 /Int 2000 , BE ) , 8 , 0 ) #Equals b"\x15\x1f|u" +Bytes padLeftBytes ( Int2Bytes ( log2Int ( ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000 ) +Int 8 /Int 8 , ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000 , BE ) , 8 , 0 ) } )
 #And { true #Equals 20000 >=Int ASSET_TRANSFER_AMOUNT:Int }
 #And { true #Equals 500000 -Int ASSET_TRANSFER_AMOUNT:Int >=Int 0 }
 #And { true #Equals 1000000 -Int ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000 >=Int 100000 }
 #And { true #Equals 18446744073709551615 >=Int ASSET_TRANSFER_AMOUNT:Int }
 #And { true #Equals 18446744073709551615 >=Int ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000 }
 #And { true #Equals ASSET_TRANSFER_AMOUNT:Int +Int 500000 >=Int 0 }
 #And { true #Equals ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000 +Int 999999000000 >=Int 100000 }
 #And { true #Equals ASSET_TRANSFER_AMOUNT:Int >=Int 0 }
 #And { true #Equals ASSET_TRANSFER_AMOUNT:Int >=Int 10000 }
```

We see a message that something went wrong with the `burn` method and a bunch of scary-looking expressions. Let's try to make sense of these expressions.

The first question we should ask is: "where are the variables from the spec?". Remember, that the spec we wanted the prover to verify was accessing the `asset_transfer.get().amount()` value, the asset transfer amount. Inside KAVM, this value becomes *symbolic* and gets the name `ASSET_TRANSFER_AMOUNT` and a sort `Int`. Anyway, where are out `precondition`s? We wanted the amount to be between 10000 and 20000, did the prover ever consider out spec? Let's sort the thing out a bit:


|   | Matching Logic                                                                                       | PyTeal                                                                    |
|:--|:-----------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------|
| 1 | `#And { true #Equals 20000 >=Int ASSET_TRANSFER_AMOUNT:Int }`                                        | `20000 >= asset_transfer.get().amount()`                                  |
| 2 | `#And { true #Equals 500000 -Int ASSET_TRANSFER_AMOUNT:Int >=Int 0 }`                                | `50000 - asset_transfer.get().amount() >= 0`                              |
| 3 | `#And { true #Equals 1000000 -Int ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000 >=Int 100000 }`      | `100000 - asset_transfer.get().amount() / 2000 * 1000 >= 100000`          |
| 4 | `#And { true #Equals 18446744073709551615 >=Int ASSET_TRANSFER_AMOUNT:Int }`                         | `MAX_UINT64 >= asset_transfer.get().amount()`                             |
| 5 | `#And { true #Equals 18446744073709551615 >=Int ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000 }`     | `MAX_UINT64 >= asset_transfer.get().amount() / 2000 * 1000`               |
| 6 | `#And { true #Equals ASSET_TRANSFER_AMOUNT:Int +Int 500000 >=Int 0 }`                                | `asset_transfer.get().amount() + 50000 >= 0`                              |
| 7 | `#And { true #Equals ASSET_TRANSFER_AMOUNT:Int /Int 2000 *Int 1000 +Int 999999000000 >=Int 100000 }` | `asset_transfer.get().amount() / 2000 * 1000 +Int 999999000000 >= 100000` |
| 8 | `#And { true #Equals ASSET_TRANSFER_AMOUNT:Int >=Int 0 }`                                            | `asset_transfer.get().amount() >= 0`                                      |
| 9 | `#And { true #Equals ASSET_TRANSFER_AMOUNT:Int >=Int 10000 }`                                        | `asset_transfer.get().amount() >= 10000`                                  |

**TODO**: more explanations

### "Symbolic execution? Matching logic?? Just give me counterexamples!"

Have you ever been feeling intimidated by formal verification? We have! That's why we want to make it *understandable*! And what's easier to understand than *concrete* examples?

When reporting the failure to verify the `burn` method, KAVM has also said:

```
INFO 2022-12-20 18:32:12 kavm.prover - Writing concrete simulation scenario to .kavm/K-Coin-Vault-burn_simulation.json
```

KAVM also can simulate Algorand smart contracts using K's concrete execution backend. Run the simulation:

```
kavm run .kavm/K-Coin-Vault-burn_simulation.json --teal-sources-dir .kavm/ --output stderr-json
```

### What's next

#### Integration with Algorand Beaker

The [Beaker](https://developer.algorand.org/articles/hello-beaker/) is an Algorand smart contract development framework that makes designing, testing, and deploying PyTeal smart contracts much easier. Since Beaker leverages `py-algorand-sdk` to interact with an Algorand node or sandbox, it will be able to use KAVM as a backend too. Yes, with Beaker we'd be able to use KAVM as a drop-in replacement for the Algorand Sandbox, thus making it trivial to bring the additional benefits of KAVM, such as fast execution and (eventually) formal verification, to any Beaker-powered project.

### Concluding remarks

KAVM is developed by [Runtime Verification](https://runtimeverification.com/) with support from the Algorand Foundation.

At Runtime Verification, we are committed to smart contract security and we would like to bring formal verification easier to adopt for every developer out there.
