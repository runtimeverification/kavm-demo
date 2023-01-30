# KAVM demo

![verify-mint-optimized](https://user-images.githubusercontent.com/8296326/212864253-f19b29da-53ee-449e-9b47-09dde7f39ab2.gif)

This is a demo project that uses [KAVM](https://github.com/runtimeverification/avm-semantics) to formally specify and verify an Algorand smart contract implemented in PyTeal. To lean more, go through the [demo](./demo.md)!

KAVM leverages the [K Framework](https://kframework.org/) to provide automated formal verification for Algorand smart contracts. KAVM integrates with [`py-algorand-sdk`](https://py-algorand-sdk.readthedocs.io/en/latest/) and [PyTeal](https://pyteal.readthedocs.io/en/stable/). You can start using KAVM for verifying your contracts today!

KAVM can be used for any PyTeal (or pure TEAL, or even [Tealish](https://github.com/tinymanorg/tealish)) project. This repository can be used as a template to set up the contract's source code to work easily with KAVM.
