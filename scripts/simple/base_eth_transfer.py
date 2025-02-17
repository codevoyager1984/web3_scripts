from web3 import Web3
from eth_account import Account
import os

# Base network RPC URL
BASE_RPC_URL = "https://mainnet.base.org"

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(BASE_RPC_URL))

def generate_wallet():
    """生成新的钱包并保存到文件"""
    account = Account.create()
    with open('layer_wallets.txt', 'a') as f:
        f.write(f"{account.address},{account.key.hex()}\n")
    return account

def transfer_eth_with_fixed_amount(private_key, to_address, amount_in_eth):
    """执行 ETH 转账"""
    from_account = Account.from_key(private_key)
    amount_in_wei = w3.to_wei(amount_in_eth, 'ether')
    
    # Build transaction
    transaction = {
        'nonce': w3.eth.get_transaction_count(from_account.address),
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
    print(f"等待交易确认... 交易哈希: {tx_hash.hex()}")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"交易成功!")
    print(f"交易哈希: {tx_receipt['transactionHash'].hex()}")
    print(f"区块号: {tx_receipt['blockNumber']}")
    print(f"Gas 消耗: {tx_receipt['gasUsed']}")
    
    return tx_receipt

def transfer_all_balance(private_key, to_address):
    """转出账户所有余额
    
    Args:
        private_key: 源账户私钥
        to_address: 目标地址
    """
    # 创建账户
    from_account = Account.from_key(private_key)
    
    # 获取账户余额
    balance = w3.eth.get_balance(from_account.address)
    
    if balance <= 0:
        raise Exception("账户余额不足")
        
    # 获取当前gas价格
    gas_price = w3.eth.gas_price
    print(f"当前gas价格: {w3.from_wei(gas_price, 'ether')} ETH")
    
    # 预估gas费用,增加20%的buffer
    gas = 21000 * 100  # 标准ETH转账gas用量
    gas_cost = gas * gas_price  # gas费用 = gas用量 * gas价格
    gas_cost_with_buffer = int(gas_cost * 1.2)  # 增加20%的buffer
    
    # 实际可转金额 = 余额 - gas费用(含buffer)
    amount_to_send = balance - gas_cost_with_buffer
    print(f"账户余额: {w3.from_wei(balance, 'ether')} ETH")
    print(f"预估gas费用: {w3.from_wei(gas_cost, 'ether')} ETH")
    print(f"gas费用(含20%buffer): {w3.from_wei(gas_cost_with_buffer, 'ether')} ETH")
    print(f"实际可转金额: {w3.from_wei(amount_to_send, 'ether')} ETH")

    if amount_to_send <= 0:
        raise Exception("余额不足以支付gas费用")
    
    # 构建交易
    transaction = {
        'nonce': w3.eth.get_transaction_count(from_account.address),
        'to': w3.to_checksum_address(to_address),
        'value': amount_to_send,
        'gas': gas,
        'gasPrice': gas_price,
        'chainId': 8453  # Base mainnet chain ID
    }
    
    # 签名交易
    signed_txn = w3.eth.account.sign_transaction(transaction, private_key)
    
    # 发送交易
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    
    # 等待交易确认
    print(f"等待交易确认... 交易哈希: {tx_hash.hex()}")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"交易成功!")
    print(f"交易哈希: {tx_receipt['transactionHash'].hex()}")
    print(f"区块号: {tx_receipt['blockNumber']}")
    print(f"Gas 消耗: {tx_receipt['gasUsed']}")
    
    return tx_receipt

def transfer_with_layers(private_key, target_address, amount_in_eth, layers=3):
    """通过多层中转钱包转账，平均 3 层转账消耗 0.000017 ETH(约 0.05 USD)
    
    Args:
        private_key: 源账户私钥
        target_address: 目标地址
        amount_in_eth: 转账金额(ETH)
        layers: 中转层数
    """
    source_account = Account.from_key(private_key)
    print(f"\n开始执行 {layers} 层中转转账...")
    print(f"源地址: {source_account.address}")
    print(f"目标地址: {target_address}")
    print(f"转账金额: {amount_in_eth} ETH")
    
    # 生成中转钱包
    layer_wallets = []
    for i in range(layers):
        wallet = generate_wallet()
        layer_wallets.append(wallet)
        print(f"生成第 {i+1} 层中转钱包: {wallet.address}")

    # 执行转账链
    current_from = source_account
    for i, wallet in enumerate(layer_wallets):
        print(f"\n执行第 {i+1} 层转账...")
        print(f"转出钱包: {current_from.address}")
        print(f"接收钱包: {wallet.address}")
        if i == 0:
            # 第一次转账使用固定金额
            transfer_eth_with_fixed_amount(current_from.key.hex(), wallet.address, amount_in_eth)
        elif i == len(layer_wallets) - 1:
            # 最后一个中转钱包转到目标地址
            transfer_all_balance(current_from.key.hex(), target_address)
        else:
            # 中间钱包转到下一个中转钱包
            transfer_all_balance(current_from.key.hex(), wallet.address)
        current_from = wallet
    
    print("\n多层转账完成!")

if __name__ == "__main__":
    # Replace with your private key
    private_key = ""
    # Test the transfer function
    to_address = ""  # Replace with the recipient's address
    amount_in_eth = 0.00005  # Replace with the amount you want to send
    transfer_with_layers(private_key, to_address, amount_in_eth)
