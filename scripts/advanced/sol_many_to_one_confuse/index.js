const {
  Connection,
  PublicKey,
  Transaction,
  SystemProgram,
  LAMPORTS_PER_SOL,
  Keypair,
} = require("@solana/web3.js");
const bs58 = require("bs58").default;
const fs = require("fs");
const path = require("path");
const winston = require("winston");

const logger = winston.createLogger({
  level: "info",
  format: winston.format.simple(),
  transports: [new winston.transports.Console()],
});

const rpcUrl =
  "https://mainnet.helius-rpc.com/?api-key=e01b426b-67c5-45e8-9e4c-57ce1062b71c";
const connection = new Connection(rpcUrl, "confirmed");

function generateWallet() {
  try {
    // 创建新的密钥对
    const wallet = Keypair.generate();

    // 获取公钥和私钥
    const publicKey = wallet.publicKey.toString();
    const secretKey = bs58.encode(wallet.secretKey);

    // Append to layer_wallets
    fs.appendFileSync(
      path.join(__dirname, "layer_wallets"),
      `${publicKey},${secretKey}\n`
    );

    return {
      publicKey,
      secretKey,
      keypair: wallet,
    };
  } catch (error) {
    throw new Error(`生成钱包失败: ${error.message}`);
  }
}

async function transferAllBalance(privateKeyString, toWalletAddress) {
  try {
    // 创建发送方的keypair
    const fromKeypair = Keypair.fromSecretKey(bs58.decode(privateKeyString));
    const fromPubkey = fromKeypair.publicKey;
    const toPubkey = new PublicKey(toWalletAddress);

    // 获取当前账户余额
    const balance = await connection.getBalance(fromPubkey);

    if (balance <= 0) {
      throw new Error("Insufficient balance to cover transaction fee");
    }

    // 获取最新的 blockhash
    const { blockhash, lastValidBlockHeight } =
      await connection.getLatestBlockhash();

    // 创建初始交易
    const transaction = new Transaction().add(
      SystemProgram.transfer({
        fromPubkey,
        toPubkey,
        lamports: balance,
      })
    );

    transaction.recentBlockhash = blockhash;
    transaction.feePayer = fromPubkey;

    // 获取预估的交易费用
    const fees = await transaction.getEstimatedFee(connection);

    if (fees === null) {
      throw new Error("Failed to estimate transaction fee");
    }

    // 计算实际可转账金额（总余额 - 交易费用）
    const transferAmount = balance - fees;

    if (transferAmount <= 0) {
      throw new Error("Insufficient balance to cover transaction fee");
    }

    // 创建新的交易，使用计算后的实际转账金额
    const finalTransaction = new Transaction().add(
      SystemProgram.transfer({
        fromPubkey,
        toPubkey,
        lamports: transferAmount,
      })
    );

    finalTransaction.recentBlockhash = blockhash;
    finalTransaction.feePayer = fromPubkey;

    // 签名交易
    finalTransaction.sign(fromKeypair);

    // 发送交易
    const rawTransaction = finalTransaction.serialize();
    const signature = await connection.sendRawTransaction(rawTransaction, {
      skipPreflight: false,
      preflightCommitment: "confirmed",
    });

    // 等待交易确认
    const confirmation = await connection.confirmTransaction({
      signature,
      blockhash,
      lastValidBlockHeight,
    });

    if (confirmation.value.err) {
      throw new Error(
        `Transaction failed: ${confirmation.value.err.toString()}`
      );
    }
    return {
      signature,
      balance,
    };
  } catch (error) {
    console.error("Error during transfer:", error);
    throw error;
  }
}

async function transferWithLayer(privateKeyString, recipientAddress, layer) {
  let currentPrivateKey = privateKeyString;
  // Send sol to last layer
  for (let i = 0; i < layer; i++) {
    const wallet = generateWallet();
    const publicKey = wallet.publicKey;
    const privateKey = wallet.secretKey;
    logger.info(`Generated layer ${i + 1} wallet: ${publicKey}`);
    const { signature, balance } = await transferAllBalance(
      currentPrivateKey,
      publicKey
    );
    logger.info(
      `Transfer to layer ${i + 1} success, amount: ${
        balance / LAMPORTS_PER_SOL
      } SOL, signature: ${signature}`
    );
    currentPrivateKey = privateKey;
  }

  // Send sol to recipient
  const { signature, balance } = await transferAllBalance(
    currentPrivateKey,
    recipientAddress
  );
  logger.info(
    `Transfer to recipient success, amount: ${
      balance / LAMPORTS_PER_SOL
    } SOL, signature: ${signature}`
  );
}

async function main() {
  // Load senders
  const senders = fs
    .readFileSync(path.join(__dirname, "senders"), "utf-8")
    .trim()
    .split("\n");

  // Load recipient addresses
  let recipientAddress = fs
    .readFileSync(path.join(__dirname, "recipient"), "utf-8")
    .trim();

  // Set batch size
  const batchSize = 10;

  // Set layer count
  const layer = 5;

  const chunks = [];
  for (let i = 0; i < senders.length; i += batchSize) {
    chunks.push(senders.slice(i, i + batchSize));
  }

  // Start transfer
  for (const chunk of chunks) {
    await Promise.all(
      chunk.map(async (senderPrivateKey) => {
        try {
          await transferWithLayer(senderPrivateKey, recipientAddress, layer);
        } catch (error) {
          logger.error(`Error during transfer: ${error.message}`);
        }
      })
    );
  }
}

main().then(() => {
  logger.info("done");
});
