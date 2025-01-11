const {
  Connection,
  PublicKey,
  Transaction,
  Keypair,
} = require("@solana/web3.js");
const {
  getAssociatedTokenAddress,
  createTransferInstruction,
} = require("@solana/spl-token");
const bs58 = require("bs58").default;
const winston = require("winston");

const logger = winston.createLogger({
  level: "info",
  format: winston.format.simple(),
  transports: [new winston.transports.Console()],
});

// 连接到 Solana 网络
const connection = new Connection(
  "https://mainnet.helius-rpc.com/?api-key=e01b426b-67c5-45e8-9e4c-57ce1062b71c",
  "confirmed"
);

async function transferAllTokens(payerKeypair, recipientAddress, mintAddress) {
  try {
    const mintAddressPubkey = new PublicKey(mintAddress);
    // 获取发送者的 Associated Token Account (ATA)
    const senderATA = await getAssociatedTokenAddress(
      mintAddressPubkey,
      payerKeypair.publicKey
    );

    // 获取接收者的 Associated Token Account (ATA)
    const recipientATA = await getAssociatedTokenAddress(
      mintAddressPubkey,
      new PublicKey(recipientAddress)
    );

    const senderAccountInfo = await connection.getParsedAccountInfo(senderATA);
    if (!senderAccountInfo.value) {
      console.log("发送者没有该代币的账户！");
      return;
    }
    const senderTokenAmount =
      senderAccountInfo.value.data.parsed.info.tokenAmount.amount;

    const senderTokenUiAmount =
      senderAccountInfo.value.data.parsed.info.tokenAmount.uiAmount;

    if (senderTokenAmount == 0) {
      throw new Error("Sender account has zero balance");
    }
    logger.info(`Sender token amount: ${senderTokenUiAmount}`);

    // 创建转账指令
    const transferInstruction = createTransferInstruction(
      senderATA, // 来源账户
      recipientATA, // 目标账户
      payerKeypair.publicKey, // 授权者
      senderTokenAmount, // 转账全部代币
      [] // 不需要额外授权
    );

    // 构建交易
    const transaction = new Transaction().add(transferInstruction);
    const latestBlockhash = await connection.getLatestBlockhash();
    transaction.recentBlockhash = latestBlockhash.blockhash;
    transaction.feePayer = payerKeypair.publicKey;

    const signature = await connection.sendTransaction(transaction, [
      payerKeypair,
    ]);
    logger.info(`Transaction sent: ${signature}`);
    await connection.confirmTransaction(
      {
        signature,
        blockhash: latestBlockhash.blockhash,
        lastValidBlockHeight: latestBlockhash.lastValidBlockHeight,
      },
      "confirmed"
    );
    logger.info(`Transaction confirmed.`);
    return signature;
  } catch (error) {
    throw error;
  }
}

// 使用示例
async function main() {
  const senderPrivateKey =
    "";
  const recipientAddress = "";
  const mintAddress = "";

  const payerKeypair = Keypair.fromSecretKey(bs58.decode(senderPrivateKey));
  await transferAllTokens(payerKeypair, recipientAddress, mintAddress);
}

main()
  .then(() => {})
  .catch((error) => {
    console.error(error);
  });
