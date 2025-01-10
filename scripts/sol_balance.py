from solana.rpc.api import Client
from solders.pubkey import Pubkey
import base58
from loguru import logger

# Mainnet RPC URL
rpc_url = "https://api.mainnet-beta.solana.com"
client = Client(rpc_url)

# Replace with your address
address = ""

pubkey = Pubkey(base58.b58decode(address))
balance = client.get_balance(pubkey).value
logger.info(f"Balance of {address} is {balance / 10 ** 9} SOL")
