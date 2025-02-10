async function testConnection() {
    const provider = new ethers.providers.JsonRpcProvider(process.env.SEPOLIA_RPC_URL);
    try {
      const blockNumber = await provider.getBlockNumber();
      console.log("Successfully connected to Sepolia. Current block number:", blockNumber);
    } catch (error) {
      console.error("Failed to connect to Sepolia:", error);
    }
  }
  
  testConnection();
  