Some commands to use for demo testing

## `kavm-demo simulate`

Simulate mint and burn on a flawed contract demo, will succeed since it does not expose the bug:

```bash
poetry run kavm-demo simulate --pyteal-code-file kcoin_vault/kcoin_vault_beaker.py --methods 'mint(100000) burn(100000)'
```

Expose the bug in the flawed contract (burn(1000) returns 0), fails:

```bash
poetry run kavm-demo simulate --pyteal-code-file kcoin_vault/kcoin_vault_beaker.py --methods 'mint(100000) burn(1000)'
```

Run the previous sequence with the fixed contract, succeeds:

```bash
poetry run kavm-demo simulate --pyteal-code-file kcoin_vault/kcoin_vault_beaker_fixed.py --methods 'mint(100000) burn(1000)'
```

## `kavm-demo verify`

```bash
poetry run kavm-demo verify --verbose --pyteal-code-file kcoin_vault/kcoin_vault_beaker.py --method mint
```
