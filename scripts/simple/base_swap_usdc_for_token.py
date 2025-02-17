from web3 import Web3
from eth_account import Account
import json
import time

class BaseUniswapV3:
    def __init__(self, provider_url, private_key):
        # 初始化 Web3 连接到 Base 链
        self.w3 = Web3(Web3.HTTPProvider(provider_url))
        self.account = Account.from_key(private_key)

        # 目标代币
        self.target_token_address = Web3.to_checksum_address("0x9e6a46f294bb67c20f1d1e7afb0bbef614403b55")
        
        # Base 链上的 USDC 地址
        self.usdc_address = Web3.to_checksum_address("0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

    def get_token_name_and_decimals(self, token_address):
        """获取代币名称和小数位数"""
        try:
            # 基本 ERC20 ABI 
            erc20_abi = json.loads('''[
                {"constant":true,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"},
                {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"},
                {"constant":true,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"payable":false,"stateMutability":"view","type":"function"}
            ]''')
            
            token_contract = self.w3.eth.contract(address=token_address, abi=erc20_abi)
            name = token_contract.functions.name().call()
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
            return name, symbol, decimals
        except Exception as e:
            print(f"获取代币信息失败: {str(e)}")
            return "Unknown", "???", 18  # 默认值

    def find_best_pool_fee(self, token_in, token_out, amount_in):
        """尝试查找最佳的池子费率"""
        fee_tiers = [100, 500, 3000, 10000]  # 0.01%, 0.05%, 0.3%, 1%
        best_fee = 3000  # 默认费率 0.3%
        best_amount_out = 0

        # Uniswap V3 Factory 地址
        factory_address = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
        
        # Factory ABI
        factory_abi = '''[{
            "inputs": [
                {"internalType": "address", "name": "tokenA", "type": "address"},
                {"internalType": "address", "name": "tokenB", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"}
            ],
            "name": "getPool",
            "outputs": [{"internalType": "address", "name": "", "type": "address"}],
            "stateMutability": "view",
            "type": "function"
        }]'''
        
        # Pool ABI
        pool_abi = '''[{
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
        }]'''

        factory = self.w3.eth.contract(
            address=Web3.to_checksum_address(factory_address),
            abi=factory_abi
        )

        print("\n开始查找最佳流动性池...")
        for fee in fee_tiers:
            try:
                # 获取池子地址
                pool_address = factory.functions.getPool(
                    Web3.to_checksum_address(token_in),
                    Web3.to_checksum_address(token_out),
                    fee
                ).call()

                if pool_address == "0x0000000000000000000000000000000000000000":
                    print(f"费率 {fee/10000}% 没有流动性池")
                    continue

                pool = self.w3.eth.contract(
                    address=Web3.to_checksum_address(pool_address),
                    abi=pool_abi
                )

                # 获取池子流动性
                liquidity = pool.functions.liquidity().call()
                
                # 获取当前价格
                slot0 = pool.functions.slot0().call()
                sqrt_price_x96 = slot0[0]
                
                # 如果池子有流动性，计算预期输出
                if liquidity > 0:
                    # 使用简单的价格计算（这是一个近似值）
                    price = (sqrt_price_x96 ** 2) / (2 ** 192)
                    amount_out = (amount_in * price) * (1 - fee/1000000)  # 考虑手续费
                    
                    print(f"费率 {fee/10000}%:")
                    print(f"- 池子地址: {pool_address}")
                    print(f"- 流动性: {liquidity}")
                    print(f"- 预计输出: {amount_out}")

                    if amount_out > best_amount_out:
                        best_amount_out = amount_out
                        best_fee = fee

            except Exception as e:
                print(f"查询费率 {fee/10000}% 时出错: {str(e)}")
                continue

        if best_amount_out == 0:
            print("\n警告: 未能找到任何有效的流动性池")
            print("请检查:")
            print("1. 代币地址是否正确")
            print("2. 是否存在交易对")
            print("3. 是否有足够的流动性")
            raise Exception("No valid liquidity pool found for the token pair")

        print(f"\n选择最佳费率: {best_fee/10000}%")
        print(f"预计输出: {best_amount_out}")
        return best_fee, best_amount_out

    def swap_usdc_for_token(self, usdc_amount, slippage_percent=1.0):
        """
        将 USDC 兑换为目标代币
        
        参数:
            usdc_amount: 要兑换的 USDC 数量（以 USDC 为单位，不是 Wei）
            slippage_percent: 滑点百分比 (默认 1%)
        """
        # 获取 USDC 的 decimals
        _, _, usdc_decimals = self.get_token_name_and_decimals(self.usdc_address)
        amount_in_wei = int(usdc_amount * (10 ** usdc_decimals))
        
        # 获取代币信息
        _, token_symbol, token_decimals = self.get_token_name_and_decimals(self.target_token_address)
        
        # 检查并授权 USDC
        erc20_abi = json.loads('''[
            {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
            {"constant":false,"inputs":[{"name":"_spender","type":"address"},{"name":"_value","type":"uint256"}],"name":"approve","outputs":[{"name":"success","type":"bool"}],"payable":false,"stateMutability":"nonpayable","type":"function"},
            {"constant":true,"inputs":[{"name":"_owner","type":"address"},{"name":"_spender","type":"address"}],"name":"allowance","outputs":[{"name":"remaining","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}
        ]''')
        
        usdc_contract = self.w3.eth.contract(address=self.usdc_address, abi=erc20_abi)
        swap_router_address = Web3.to_checksum_address("0x2626664c2603336E57B271c5C0b26F421741e481")
        
        # 检查余额
        balance = usdc_contract.functions.balanceOf(self.account.address).call()
        if balance < amount_in_wei:
            raise Exception(f"USDC 余额不足. 需要: {usdc_amount}, 当前余额: {balance / (10 ** usdc_decimals)}")
        
        # 检查授权
        allowance = usdc_contract.functions.allowance(self.account.address, swap_router_address).call()
        print(f"当前授权 USDC: {allowance}")
        if allowance < amount_in_wei:
            print("需要授权 USDC...")
            approve_txn = usdc_contract.functions.approve(
                swap_router_address,
                amount_in_wei  # 只授权需要兑换的数量
            ).build_transaction({
                'from': self.account.address,
                'nonce': self.w3.eth.get_transaction_count(self.account.address),
                'gas': 100000,
                'gasPrice': self.w3.eth.gas_price
            })
            
            signed_approve_txn = self.w3.eth.account.sign_transaction(approve_txn, self.account.key)
            approve_tx_hash = self.w3.eth.send_raw_transaction(signed_approve_txn.raw_transaction)
            print(f"等待授权交易确认... 交易哈希: {approve_tx_hash.hex()}")
            self.w3.eth.wait_for_transaction_receipt(approve_tx_hash)
            print("授权完成")
        
        # 查找最佳费率
        best_fee, amount_out_quote = self.find_best_pool_fee(
            self.usdc_address, 
            self.target_token_address,
            amount_in_wei
        )
        
        # 计算考虑滑点的最小输出
        min_amount_out = int(amount_out_quote * (100 - slippage_percent) / 100)
        print(f"min_amount_out: {min_amount_out}")
        
        # 使用 SwapRouter
        swap_router_abi = json.loads('''[
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
        ]''')
        swap_router = self.w3.eth.contract(address=swap_router_address, abi=swap_router_abi)
        
        # 构建交易参数
        params = {
            'tokenIn': self.usdc_address,
            'tokenOut': self.target_token_address,
            'fee': best_fee,
            'recipient': self.account.address,
            'amountIn': amount_in_wei,
            'amountOutMinimum': min_amount_out,
            'sqrtPriceLimitX96': 0
        }
        
        # 获取当前 gas 价格
        gas_price = self.w3.eth.gas_price
        gas_price_adjusted = int(gas_price * 1.2)
        
        # 估算 gas 用量
        gas_estimate = 400000  # 默认预估
        try:
            gas_estimate = swap_router.functions.exactInputSingle(
                params
            ).estimate_gas({
                'from': self.account.address
            })
            gas_estimate = int(gas_estimate * 1.2)
        except Exception as e:
            print(f"Gas 估算失败，使用默认值: {str(e)}")
        
        # 构建交易
        transaction = swap_router.functions.exactInputSingle(
            params
        ).build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': gas_estimate,
            'gasPrice': gas_price_adjusted,
            'value': 0,  # 不需要发送 ETH
            'chainId': 8453
        })
        
        # 输出交易信息
        print(f"准备将 {usdc_amount} USDC 兑换为 {token_symbol}")
        print(f"预期最少获得: {min_amount_out / (10 ** token_decimals)} {token_symbol}")
        print(f"Gas 估算: {gas_estimate} 单位")
        print(f"Gas 价格: {self.w3.from_wei(gas_price_adjusted, 'gwei')} Gwei")
        
        # 签名并发送交易
        signed_txn = self.w3.eth.account.sign_transaction(
            transaction,
            self.account.key
        )
        
        print("交易已签名，正在发送...")
        tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"交易已提交，交易哈希: {tx_hash.hex()}")
        
        try:
            print("等待交易确认...")
            tx_receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
            print(f"交易已确认在区块 {tx_receipt['blockNumber']}")
            
            if tx_receipt['status'] == 1:
                print("交易成功执行!")
                # 查询获得了多少代币
                erc20_abi = json.loads('''[
                    {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"}
                ]''')
                token_contract = self.w3.eth.contract(address=self.target_token_address, abi=erc20_abi)
                balance = token_contract.functions.balanceOf(self.account.address).call()
                print(f"当前 {token_symbol} 余额: {balance / (10 ** token_decimals)}")
            else:
                print("交易执行失败!")
            
            return tx_receipt
        except Exception as e:
            print(f"等待交易确认时出错: {str(e)}")
            print(f"可以在区块浏览器中查看交易状态: https://basescan.org/tx/{tx_hash.hex()}")
            return None

# 使用示例
def main():
    # 初始化配置
    provider_url = 'https://mainnet.base.org'  # Base 链的 RPC URL
    private_key = ''  # 替换为你的私钥
    
    # 创建 Base Uniswap 实例
    base_uniswap = BaseUniswapV3(provider_url, private_key)
    
    # 获取目标代币信息
    token_name, token_symbol, _ = base_uniswap.get_token_name_and_decimals(
        base_uniswap.target_token_address
    )
    print(f"目标代币: {token_name} ({token_symbol})")
    
    # 检查 USDC 余额
    usdc_contract = base_uniswap.w3.eth.contract(
        address=base_uniswap.usdc_address,
        abi=json.loads('''[
            {"constant":true,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"payable":false,"stateMutability":"view","type":"function"},
            {"constant":true,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"payable":false,"stateMutability":"view","type":"function"}
        ]''')
    )
    usdc_balance = usdc_contract.functions.balanceOf(base_uniswap.account.address).call()
    usdc_decimals = usdc_contract.functions.decimals().call()
    usdc_balance_formatted = usdc_balance / (10 ** usdc_decimals)
    print(f"当前账户 USDC 余额: {usdc_balance_formatted} USDC")
    
    # 设置要兑换的 USDC 数量
    usdc_to_swap = 0.01  # 兑换 0.01 USDC
    
    # 确保有足够的余额
    if usdc_balance_formatted < usdc_to_swap:
        print(f"警告: USDC 余额不足! 当前余额: {usdc_balance_formatted} USDC")
        return
    
    # 执行兑换
    try:
        tx_receipt = base_uniswap.swap_usdc_for_token(usdc_to_swap)
        if tx_receipt and tx_receipt['status'] == 1:
            print(f"成功将 {usdc_to_swap} USDC 兑换为 {token_symbol}")
        else:
            print("兑换操作失败或尚未确认")
    except Exception as e:
        print(f"兑换过程中出错: {str(e)}")

if __name__ == "__main__":
    main()