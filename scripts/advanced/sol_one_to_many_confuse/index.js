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

async function transferWithFixedAmount(
  privateKeyString,
  recipientAddress,
  amountInLamports
) {
  const fromKeypair = Keypair.fromSecretKey(bs58.decode(privateKeyString));
  const fromPubkey = fromKeypair.publicKey;
  const toPubkey = new PublicKey(recipientAddress);
  // 获取最新的 blockhash
  const { blockhash, lastValidBlockHeight } =
    await connection.getLatestBlockhash();
  const transaction = new Transaction().add(
    SystemProgram.transfer({
      fromPubkey,
      toPubkey,
      lamports: amountInLamports,
    })
  );

  transaction.recentBlockhash = blockhash;
  transaction.feePayer = fromPubkey;
  transaction.sign(fromKeypair);

  const rawTransaction = transaction.serialize();
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
    throw new Error(`Transaction failed: ${confirmation.value.err.toString()}`);
  }

  return signature;
}

async function transferAllBalance(privateKeyString, toWalletAddress) {
  try {
    // 创建发送方的keypair
    const fromKeypair = Keypair.fromSecretKey(bs58.decode(privateKeyString));
    const fromPubkey = fromKeypair.publicKey;
    const toPubkey = new PublicKey(toWalletAddress);

    // 获取当前账户余额
    const balance = await connection.getBalance(fromPubkey);

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
    return signature;
  } catch (error) {
    console.error("Error during transfer:", error);
    throw error;
  }
}

async function transferWithLayer(
  privateKeyString,
  recipientAddress,
  amountInLamports,
  layer
) {
  let currentPrivateKey = privateKeyString;

  // Send sol to last layer
  for (let i = 0; i < layer; i++) {
    const wallet = generateWallet();
    const publicKey = wallet.publicKey;
    const privateKey = wallet.secretKey;
    logger.info(`Generated layer ${i + 1} wallet: ${publicKey}`);
    if (i === 0) {
      const signature = await transferWithFixedAmount(
        currentPrivateKey,
        publicKey,
        amountInLamports
      );
      logger.info(
        `Transfer to layer ${i + 1} success, amount: ${
          amountInLamports / LAMPORTS_PER_SOL
        } SOL, signature: ${signature}`
      );
    } else {
      const signature = await transferAllBalance(currentPrivateKey, publicKey);
      logger.info(
        `Transfer to layer ${i + 1} success, amount: ${
          amountInLamports / LAMPORTS_PER_SOL
        } SOL, signature: ${signature}`
      );
    }
    currentPrivateKey = privateKey;
  }

  // Send sol to recipient
  const signature = await transferAllBalance(
    currentPrivateKey,
    recipientAddress
  );
  logger.info(
    `Transfer to recipient success, amount: ${
      amountInLamports / LAMPORTS_PER_SOL
    } SOL, signature: ${signature}`
  );
}

async function main() {
  // Load private key
  const privateKeyString = fs
    .readFileSync(path.join(__dirname, "private_key"), "utf-8")
    .trim();

  // Load recipient addresses
  let recipientAddresses = fs
    .readFileSync(path.join(__dirname, "recipients"), "utf-8")
    .trim()
    .split("\n");
  recipientAddresses = recipientAddresses.map((address) => address.trim());

  // Set batch size
  const batchSize = 10;

  // Set layer count
  const layer = 5;

  const chunks = [];
  for (let i = 0; i < recipientAddresses.length; i += batchSize) {
    chunks.push(recipientAddresses.slice(i, i + batchSize));
  }

  // Start transfer
  for (const chunk of chunks) {
    await Promise.all(
      chunk.map(async (recipientAddress) => {
        try {
          // Change amount in SOL, you can set in fixed amount or random amount
          const amountInSol = 0.001;
          const amountInLamports = amountInSol * LAMPORTS_PER_SOL;

          await transferWithLayer(
            privateKeyString,
            recipientAddress,
            amountInLamports,
            layer
          );
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
