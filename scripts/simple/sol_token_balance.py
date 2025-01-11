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
# Replace with your token mint address, for example: USDT
token_mint_address = "EG1Y8goUGa7y4iRYRgLgwBmSHc4Lxc91qL35cdDNBiRc"

pubkey = Pubkey(base58.b58decode(address))

data = client.get_token_accounts_by_owner_json_parsed(
    pubkey,
    TokenAccountOpts(
        mint=Pubkey(base58.b58decode(token_mint_address)),
    ),
)

balance = data.value[0].account.data.parsed['info']['tokenAmount']['uiAmount']
logger.info(f"Balance of token {token_mint_address} is {balance}")
