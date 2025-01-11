# SOL One to Many with Confuse

This script is used to send SOL to from one wallet to many other wallets with confuse. And the fee is quite cheap, only 0.000005 SOL per transaction(layer).

## 1. How much fee cost?

For 1 transaction(layer per wallet), the fee is 0.000005 SOL, see if you has 1000 wallets, and set the layer to 5, the total fee will be 0.000005 * 5 * 1000 = 0.025 SOL.

## 2. Configuration

### Wallets

- `private_key`: Add your private key in `private_key` file.
- `recipients`: Add the recipient addresses in `recipients` file.

### Options

- `rpcUrl`: Change the rpc url if needed.
- `layer`: Set the layer count, the more layer, the more confuse, but the fee will be higher.
- `batchSize`: Set the batch size.
- `amountInSol`: Set the amount of SOL to transfer.

## 3. How to run?

Run from the root directory

```bash
node scripts/advanced/sol_one_to_many_confuse/index.js
```

After each run, auto generated wallets will be saved in `layer_wallets` file.
