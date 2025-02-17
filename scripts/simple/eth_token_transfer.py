from web3 import Web3
from eth_account import Account
import json

# Base network RPC URL
RPC_URL = "https://mainnet.base.org"
w3 = Web3(Web3.HTTPProvider(RPC_URL))

# USDC contract address on Base
USDC_ADDRESS = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

# USDC ABI - minimal for transfer
USDC_ABI = [
    {
        "inputs": [
            {"name": "to", "type": "address"},
            {"name": "amount", "type": "uint256"}
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def transfer_usdc(private_key, to_address, amount):
    # Create account from private key
    account = Account.from_key(private_key)
    
    # Initialize USDC contract
    usdc_contract = w3.eth.contract(address=USDC_ADDRESS, abi=USDC_ABI)
    
    # Build transaction
    nonce = w3.eth.get_transaction_count(account.address)
    
    # USDC uses 6 decimals
    amount_in_wei = int(amount * 10**6)  # Convert to integer
    
    transaction = usdc_contract.functions.transfer(
        Web3.to_checksum_address(to_address),
        amount_in_wei
    ).build_transaction({
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
        'chainId': 8453  # Base mainnet chain ID
    })
    
    # Sign and send transaction
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    print(f"Waiting for transaction {tx_hash.hex()} to be mined...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction successful!")
    print(f"Transaction hash: {tx_receipt['transactionHash'].hex()}")
    print(f"Block number: {tx_receipt['blockNumber']}")
    print(f"Gas used: {tx_receipt['gasUsed']}")

    return tx_hash.hex()

# Example usage:
private_key = ""
to_address = ""
amount = 0.001  # Amount in USDC
tx_hash = transfer_usdc(private_key, to_address, amount)
print(f"Transaction hash: {tx_hash}")
