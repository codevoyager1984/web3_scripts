from web3 import Web3
from eth_account import Account
import json
import time


class UniswapV3:
    def __init__(self, rpc_url, chain_id, eth_token_address, private_key):
        """Initialize UniswapV3 trading class

        Args:
            rpc_url: RPC URL of the blockchain node, for example: https://mainnet.base.org
            chain_id: Chain ID (e.g. Base chain is 8453)
            eth_token_address: ETH token address (e.g. 0x4200000000000000000000000000000000000006 for WETH)
            private_key: User wallet private key
        """
        # Initialize Web3 connection to Base chain
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.account = Account.from_key(private_key)
        self.chain_id = chain_id
        self.eth_token_address = Web3.to_checksum_address(eth_token_address)

    def get_token_name_and_decimals(self, token_address):
        """Get token name and decimals"""
        try:
            # Basic ERC20 ABI
            erc20_abi = json.loads(
                """[
                {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},
                {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},
                {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"}
            ]"""
            )

            token_contract = self.w3.eth.contract(address=token_address, abi=erc20_abi)
            name = token_contract.functions.name().call()
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
            return name, symbol, decimals
        except Exception as e:
            print(f"Failed to get token info: {str(e)}")
            return "Unknown", "???", 18  # Default values

    def find_best_pool_fee(self, token_in, token_out, amount_in):
        """Try to find the best pool fee rate"""
        fee_tiers = [100, 500, 2500, 10000]  # 0.01%, 0.05%, 0.25%, 1%
        best_fee = 2500  # Default fee 0.25%
        best_amount_out = 0

        # Uniswap V3 Factory address
        factory_address = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"

        # Factory ABI
        factory_abi = """[{
            "inputs": [
                {"internalType": "address", "name": "tokenA", "type": "address"},
                {"internalType": "address", "name": "tokenB", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"}
            ],
            "name": "getPool",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        }]"""

        # Pool ABI
        pool_abi = """[{
            "inputs": [],
            "name": "slot0",
            "outputs": [
                {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
                {"internalType": "int24", "name": "tick", "type": "int24"},
                {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
                {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
                {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
                {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
                {"internalType": "bool", "name": "unlocked", "type": "bool"}
            ],
            "stateMutability": "view",
            "type": "function"
        }, {
            "inputs": [],
            "name": "liquidity",
            "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
            "stateMutability": "view",
            "type": "function"
        }]"""

        factory = self.w3.eth.contract(
            address=Web3.to_checksum_address(factory_address), abi=factory_abi
        )

        print("\nStarting to find best liquidity pool...")
        for fee in fee_tiers:
            try:
                # Get pool address
                pool_address = factory.functions.getPool(
                    Web3.to_checksum_address(token_in),
                    Web3.to_checksum_address(token_out),
                    fee,
                ).call()
                if pool_address == "0x0000000000000000000000000000000000000000":
                    print(f"Fee {fee/10000}% has no liquidity pool")
                    continue

                pool = self.w3.eth.contract(
                    address=Web3.to_checksum_address(pool_address), abi=pool_abi
                )
                # Get pool liquidity
                liquidity = pool.functions.liquidity().call()

                # Get current price
                slot0 = pool.functions.slot0().call()
                sqrt_price_x96 = slot0[0]
                # If pool has liquidity, calculate expected output
                if liquidity > 0:
                    # Use simple price calculation (this is an approximation)
                    price = (sqrt_price_x96**2) / (2**192)
                    amount_out = (amount_in * price) * (
                        1 - fee / 1000000
                    )  # Consider fee

                    print(f"Fee {fee/10000}%:")
                    print(f"- Pool address: {pool_address}")
                    print(f"- Liquidity: {liquidity}")
                    print(f"- Expected output: {amount_out}")

                    if amount_out > best_amount_out:
                        best_amount_out = amount_out
                        best_fee = fee
                        break
                else:
                    print(f"Fee {fee/10000}% has no liquidity")

            except Exception as e:
                print(f"Error querying fee {fee/10000}%: {str(e)}")
                continue

        if best_amount_out == 0:
            print("\nWarning: Could not find any valid liquidity pool")
            print("Please check:")
            print("1. Token addresses are correct")
            print("2. Trading pair exists")
            print("3. Sufficient liquidity exists")
            raise Exception("No valid liquidity pool found for the token pair")

        print(f"\nSelected best fee: {best_fee/10000}%")
        print(f"Expected output: {best_amount_out}")
        return best_fee, best_amount_out

    def swap_eth_for_token(
        self, eth_amount, target_token_address, slippage_percent=1.0
    ):
        """
        Swap ETH for target token

        Args:
            eth_amount: Amount of ETH to swap (in ETH units, not Wei)
            slippage_percent: Slippage percentage (default 1%)
        """
        target_token_address = Web3.to_checksum_address(target_token_address)
        # Get target token info
        token_name, token_symbol, _ = self.get_token_name_and_decimals(
            target_token_address
        )
        print(f"Target token: {token_name} ({token_symbol})")
        # Check ETH balance
        eth_balance = self.w3.eth.get_balance(self.account.address)
        eth_balance_formatted = self.w3.from_wei(eth_balance, "ether")
        print(f"Current account ETH balance: {eth_balance_formatted} ETH")
        # Ensure sufficient balance
        if eth_balance_formatted < eth_amount:
            raise Exception(
                f"Warning: Insufficient ETH balance! Current balance: {eth_balance_formatted} ETH"
            )

        # Convert ETH to Wei
        amount_in_wei = self.w3.to_wei(eth_amount, "ether")

        # Get token info
        _, token_symbol, token_decimals = self.get_token_name_and_decimals(
            target_token_address
        )

        # Find best fee rate
        best_fee, amount_out_quote = self.find_best_pool_fee(
            self.eth_token_address, target_token_address, amount_in_wei
        )

        # Calculate minimum output considering slippage
        min_amount_out = int(amount_out_quote * (100 - slippage_percent) / 100)

        # Use SwapRouter
        swap_router_address = Web3.to_checksum_address(
            "0x2626664c2603336E57B271c5C0b26F421741e481"
        )
        swap_router_abi = json.loads(
            """[
            {
                "inputs": [
                    {
                        "components": [
                            {
                                "internalType": "address",
                                "name": "tokenIn",
                                "type": "address"
                            },
                            {
                                "internalType": "address",
                                "name": "tokenOut",
                                "type": "address"
                            },
                            {
                                "internalType": "uint24",
                                "name": "fee",
                                "type": "uint24"
                            },
                            {
                                "internalType": "address",
                                "name": "recipient",
                                "type": "address"
                            },
                            {
                                "internalType": "uint256",
                                "name": "amountIn",
                                "type": "uint256"
                            },
                            {
                                "internalType": "uint256",
                                "name": "amountOutMinimum",
                                "type": "uint256"
                            },
                            {
                                "internalType": "uint160",
                                "name": "sqrtPriceLimitX96",
                                "type": "uint160"
                            }
                        ],
                        "internalType": "struct ISwapRouter.ExactInputSingleParams",
                        "name": "params",
                        "type": "tuple"
                    }
                ],
                "name": "exactInputSingle",
                "outputs": [
                    {
                        "internalType": "uint256",
                        "name": "amountOut",
                        "type": "uint256"
                    }
                ],
                "stateMutability": "payable",
                "type": "function"
            }
        ]"""
        )
        swap_router = self.w3.eth.contract(
            address=swap_router_address, abi=swap_router_abi
        )

        # Build transaction parameters
        params = {
            "tokenIn": self.eth_token_address,
            "tokenOut": target_token_address,
            "fee": best_fee,
            "recipient": self.account.address,
            "amountIn": amount_in_wei,
            "amountOutMinimum": min_amount_out,
            "sqrtPriceLimitX96": 0,
        }

        # Get current gas price
        gas_price = self.w3.eth.gas_price
        gas_price_adjusted = int(gas_price * 1.2)

        # Estimate gas usage
        gas_estimate = 400000  # Default estimate
        try:
            gas_estimate = swap_router.functions.exactInputSingle(params).estimate_gas(
                {"from": self.account.address, "value": amount_in_wei}
            )
            gas_estimate = int(gas_estimate * 1.2)
        except Exception as e:
            print(f"Gas estimation failed, using default value: {str(e)}")

        # Build transaction
        transaction = swap_router.functions.exactInputSingle(params).build_transaction(
            {
                "from": self.account.address,
                "nonce": self.w3.eth.get_transaction_count(self.account.address),
                "gas": gas_estimate,
                "gasPrice": gas_price_adjusted,
                "value": amount_in_wei,  # Send ETH
                "chainId": self.chain_id,
            }
        )

        # Output transaction info
        print(f"Preparing to swap {eth_amount} ETH for {token_symbol}")
        print(
            f"Expected minimum: {min_amount_out / (10 ** token_decimals)} {token_symbol}"
        )
        print(f"Gas estimate: {gas_estimate} units")
        print(f"Gas price: {self.w3.from_wei(gas_price_adjusted, 'gwei')} Gwei")

        # Sign and send transaction
        signed_txn = self.w3.eth.account.sign_transaction(transaction, self.account.key)

        print("Transaction signed, sending...")
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"Transaction submitted, hash: {tx_hash.hex()}")

        try:
            print("Waiting for transaction confirmation...")
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            print(f"Transaction confirmed in block {tx_receipt['blockNumber']}")

            if tx_receipt["status"] == 1:
                print("Transaction executed successfully!")
                # Query received token amount
                erc20_abi = json.loads(
                    """[
                    {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}
                ]"""
                )
                token_contract = self.w3.eth.contract(
                    address=target_token_address, abi=erc20_abi
                )
                balance = token_contract.functions.balanceOf(
                    self.account.address
                ).call()
                print(
                    f"Current {token_symbol} balance: {balance / (10 ** token_decimals)}"
                )
            else:
                raise Exception("Transaction execution failed!")
            if tx_receipt and tx_receipt["status"] == 1:
                print(f"Successfully swapped {eth_amount} ETH for {token_symbol}")
            else:
                raise Exception("Swap operation failed or not confirmed")
        except Exception as e:
            print(f"Error waiting for transaction confirmation: {str(e)}")
            print(
                f"You can check transaction status at: https://basescan.org/tx/{tx_hash.hex()}"
            )
            return None


if __name__ == "__main__":
    rpc_url = "https://mainnet.base.org"  # Base chain RPC URL
    chain_id = 8453
    private_key = ""  # Replace with your private key
    source_token_address = "0x4200000000000000000000000000000000000006"  # WETH
    target_token_address = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # USDC

    client = UniswapV3(
        rpc_url=rpc_url,
        chain_id=chain_id,
        eth_token_address=source_token_address,
        private_key=private_key,
    )
    client.swap_eth_for_token(
        eth_amount=0.000001,
        target_token_address=target_token_address,
        slippage_percent=1.0,
    )
