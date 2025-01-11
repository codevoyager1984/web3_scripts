const {
    Connection,
    PublicKey,
    Transaction,
    SystemProgram,
    LAMPORTS_PER_SOL,
    Keypair,
} = require("@solana/web3.js");
const bs58 = require("bs58").default;

async function transferAllBalance(
  fromPrivateKey,
  toWalletAddress,
  rpcUrl = "https://mainnet.helius-rpc.com/?api-key=e01b426b-67c5-45e8-9e4c-57ce1062b71c"
) {
  try {
    const connection = new Connection(rpcUrl, "confirmed");

    // 创建发送方的keypair
    const fromKeypair = Keypair.fromSecretKey(bs58.decode(fromPrivateKey));
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

    console.log("Transfer successful!");
    console.log("Signature:", signature);
    console.log(
      "Transferred amount:",
      transferAmount / LAMPORTS_PER_SOL,
      "SOL"
    );
    console.log("Transaction fee:", fees / LAMPORTS_PER_SOL, "SOL");

    return signature;
  } catch (error) {
    console.error("Error during transfer:", error);
    throw error;
  }
}

async function main() {
  try {
    const privateKeyString =
      "";
    const toWalletAddress = "";

    if (!privateKeyString || !toWalletAddress) {
      throw new Error(
        "Missing environment variables (WALLET_PRIVATE_KEY or RECIPIENT_ADDRESS)"
      );
    }

    await transferAllBalance(privateKeyString, toWalletAddress);
  } catch (error) {
    console.error("Main error:", error);
    process.exit(1);
  }
}

main().then(() => {
  console.log("done");
});
