## Try KAVM

KAVM provides property-tetsing capabilities to any Algorand smart contract:

![failing-test.gif](https://user-images.githubusercontent.com/8296326/203583716-e8937d02-f186-4862-b36c-26abc3cdf578.gif)

Read on if you'd like to learn more!

### How to install KAVM

#### Install kup tool

The easiest way to install KAVM is provided by the kup tool. To install kup, run the following in your terminal:

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

In the screenshot above, we see kup reporting that the `kavm` package is available for installation. Proceed by typing `kup install kavm` to install it:

![2](https://user-images.githubusercontent.com/8296326/202645178-324a8bd2-cd8e-4eee-920d-6b4c65dd1241.png)

The installation process may take some time, since `kavm` will be built from source, together with its dependencies.

### KAVM demo: catching rounding errors

Rounding errors is smart contract can lead to severe security vulnerabilities and loss of funds. Rounding errors analysis is an important step are always perform in every smart contract audit that we do at Runtime Verification.

In this tutorial, we will look at an Algorand smart contract implemented in PyTeal, which implements a Vault for K Coins. Users can interact with the Vault to *mint* K Coins in exchange for their Algos and to *burn* their K Coins to redeem the Algos. We will use KAVM in conjunction with [Hypothesis](https://hypothesis.readthedocs.io/en/latest/index.html), a Python property-based testing framework, to check that the rounding errors in the contract are *bounded*, i.e. always remain negligible. Checking that property allows to ensure that neither can users make money out of thin air, nor will they loose any Alogs while interacting with the Vault .

#### The K Coin Vault contract

The contract uses the PyTeal `Router` abstraction to define the [ABI](https://pyteal.readthedocs.io/en/stable/abi.html) of the contract, and plug the methods implementations into it. Let us have a look at the interface of the contract, with the implementation of the methods stripped down (full code available [here](https://github.com/runtimeverification/kavm-demo)):

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
def mint(payment: abi.PaymentTransaction, *, output: abi.Uint64) -> Expr:
    """
    Mint K Coins, issuing an inner asset transfer transaction to sender if successful
    Args:
        payment: A payment transaction containing the amount of Algos the user wishes to mint with.
            The receiver of this transaction must be this app's escrow account.
    Returns: minted amount of K Coins that the user gets
    """
    pass


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

To test PyTeal contracts, the developers have to *deploy* them, since the source code above cannot be executed directly. The usual deployment workflow is to compile the contract's source code to TEAL, the executable language of the Algorand blockchain, and submit an application call transaction to an Algorand node that will create the contract. Interaction with the created contract is then done by submitting more application call transactions.

KAVM works a little differently. KAVM is not an implementation of the Algorand node, but rather a simulation and formal verification tool for Algorand smart contracts. Therefore, KAVM runs locally on the developer's machine, almost like the Algorand [Sandbox](https://github.com/algorand/sandbox). However, in contracts to the Sandbox, there is no HTTP communication involved when interacting with KAVM, therefore the gap between the Python testing/deployment script and the execution engine is much narrower.

With all that being said, we do not want the developers to think too much about the implementation details! Thus, we have designed KAVM to integrate well with `py-algorand-sdk`, making it possible to interact with KAVM almost as if it were, in fact, and Algorand node.

Enough talking! Let's get our hand dirt and simulate the K Coin Vault contract with KAVM!

#### Testing the K Coin Vault with KAVM

We have packaged the contract's source code and testing scripts into a tiny Python package. The package sets-up the Python environment with the `poetry` tool and provides testing code. In case you do not have `poetry` installed, you can run the official [installer script](https://python-poetry.org/docs/#installation) like this:

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

Once `poetry` is set-up, close the `kavm-demo` repository and change into it:

```bash
git clone https://github.com/runtimeverification/kavm-demo.git
cd kavm-demo
```

Inside the directory, there's a bunch of files that define the project structure, and as well the `kcoin_vault` directory, which contains the Vault implementation in PyTeal, along with the `clinet.py` to interact with the contract and the test files:

```bash
$ ls kcoin_vault
client.py    __init__.py __main__.py  test_mint_burn.py conftest.py  kcoin_vault_pyteal.py
```

The `kcoin_vault_pyteal.py` contains the full implementation of the Vault contract in PyTeal. We will look at it later (it is not long at all though). Let's instead first look at `test_mint_burn.py`, which defines a property test of minting and burning in sequence:

```python
@settings(deadline=TEST_CASE_DEADLINE, max_examples=N_TESTS, phases=[Phase.generate])
@given(
    microalgos=st.integers(min_value=MIN_ARG_VALUE, max_value=MAX_ARG_VALUE),
)
def test_mint_burn(initial_state_fixture, microalgos: int) -> None:
    client, user_addr, user_private_key = initial_state_fixture
    minted = client.call_mint(user_addr, user_private_key, microalgos)
    got_back = client.call_burn(user_addr, user_private_key, minted)
    assert got_back == microalgos
```

The test scenario is simple:
* The contract is initialized in the `initial_state_fixture`, defined in `conftest.py`. The initialization happens only once, and every test case that Hypothesis generates share the same instance.
* We call the `'mint'` method of the contract supplying the *given* amount of microalgos which will be between `MIN_ARG_VALUE` and `MAX_ARG_VALUE`
* Upon successful minting, we straight away make a call to the `'burn'` method with the amount we have minted
* We expect that the redeemed amount is going to be the same that the one we had in hand initially, however...

Let's see what KAVM and Hypothesis think about it:

```
$ poetry run prop-test kcoin_vault/test_mint_burn.py
```

![failing-test.gif](https://user-images.githubusercontent.com/8296326/203583716-e8937d02-f186-4862-b36c-26abc3cdf578.gif)

The scary red output indicates that Hypothesis has found a value of the `microalgos` parameter that violates the `got_back == microalgos` assertion. The message essentially says that we have minted with 169869 microalgos, but only got 169868 back

```
- during generate phase (5.62 seconds):
  - Typical runtimes: 387-554 ms, ~ 0% in data generation
  - 11 passing examples, 1 failing examples, 0 invalid examples
  - Found 1 distinct error in this phase

- Stopped because nothing left to do
```
