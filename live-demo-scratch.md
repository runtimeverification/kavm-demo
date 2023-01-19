Start with going through the contract and talking about pre-/post-conditions interface and how we can adapt it to Beaker.

## Verify `mint` --- how a successful proof looks

Demonstrate `kavm-demo --verify` for the `mint` method of the flawed contract:

```
poetry run kavm-demo verify --pyteal-code-file kcoin_vault/kcoin_vault_pyteal.py --method mint
```

That should take about 4min to finish. While it's crunching, have a look at the generated K spec in `.kavm/k-coin-vault-mint-spec.k`. Most of the file is to K-specific (it's a K spec!), but the `requries` and `ensires` clauses at the bottom are worth looking at. Compare them to the spec in the PyTeal file.

## Verify `burn` --- how a failing proof looks

Try the `burn` method now, which will fail:

```
poetry run kavm-demo verify --pyteal-code-file kcoin_vault/kcoin_vault_pyteal.py --method burn
```

This will fail with a rather scary constraint. 
