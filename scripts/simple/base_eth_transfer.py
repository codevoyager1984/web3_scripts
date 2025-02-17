from web3 import Web3
from eth_account import Account
import os

# Base network RPC URL
BASE_RPC_URL = "https://mainnet.base.org"

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

# Replace with your private key
private_key = ""
account = Account.from_key(private_key)

def transfer_eth(to_address, amount_in_eth):
    # Convert ETH to Wei
    amount_in_wei = w3.to_wei(amount_in_eth, 'ether')
    
    # Build transaction
    transaction = {
        'nonce': w3.eth.get_transaction_count(account.address),
        'to': w3.to_checksum_address(to_address),
        'value': amount_in_wei,
        'gas': 21000,
        'gasPrice': w3.eth.gas_price,
        'chainId': 8453  # Base mainnet chain ID
    }
    
    # Sign transaction
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
    
    # Send transaction
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    # Wait for transaction receipt
    print(f"Waiting for transaction {tx_hash.hex()} to be mined...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction successful!")
    print(f"Transaction hash: {tx_receipt['transactionHash'].hex()}")
    print(f"Block number: {tx_receipt['blockNumber']}")
    print(f"Gas used: {tx_receipt['gasUsed']}")
    
    return tx_receipt

if __name__ == "__main__":
    # Test the transfer function
    to_address = ""  # Replace with the recipient's address
    amount_in_eth = 0.00001  # Replace with the amount you want to send
    transfer_eth(to_address, amount_in_eth)
