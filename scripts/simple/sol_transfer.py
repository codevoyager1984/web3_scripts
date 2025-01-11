from decimal import Decimal
import time
import base58
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.message import Message
from solders.transaction import Transaction
from solana.rpc.api import Client
from solders.system_program import TransferParams, transfer
from solana.rpc.types import TxOpts
from loguru import logger

rpc_url = "https://api.mainnet-beta.solana.com"
client = Client(rpc_url)

# Sender and recipient
sender_private_key = ""
recipient_address = ""

sender: Keypair = Keypair.from_base58_string(sender_private_key)
recipient_pubkey = Pubkey(base58.b58decode(recipient_address))

# Set amount to transfer
sol_amount = Decimal("0.001")
sol_lamports = Decimal("1e+9")

latest_blockhash = client.get_latest_blockhash()
recent_blockhash = latest_blockhash.value.blockhash

tx = Transaction(
    from_keypairs=[sender],
    message=Message(
        instructions=[
            transfer(TransferParams(from_pubkey=sender.pubkey(), to_pubkey=recipient_pubkey, lamports=int(sol_amount * sol_lamports))),
        ],
        payer=sender.pubkey(),
    ),
    recent_blockhash=recent_blockhash,
)

tx_resp = client.send_transaction(tx, opts=TxOpts(skip_preflight=True))
logger.info(f"Transaction signature: {tx_resp.value}")

client.confirm_transaction(tx_resp.value)


