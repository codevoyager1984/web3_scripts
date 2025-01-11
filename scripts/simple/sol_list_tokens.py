from solana.rpc.api import Client
from solana.rpc.types import TokenAccountOpts
from solders.pubkey import Pubkey
import base58
from loguru import logger

# Mainnet RPC URL
rpc_url = "https://api.mainnet-beta.solana.com"
client = Client(rpc_url)

# Replace with your address
address = ""

pubkey = Pubkey(base58.b58decode(address))

data = client.get_token_accounts_by_owner_json_parsed(
    pubkey,
    TokenAccountOpts(
        # TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA is the program id for SOL
        program_id=Pubkey(base58.b58decode("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")),
    ),
)

token_count = len(data.value)
logger.info(f'Token count: {token_count}, Token list: {data.value}')
