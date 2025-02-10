
# An Empirical Smart Contracts Latency Analysis on Ethereum Blockchain for Trustworthy Inter-Provider Agreements

## Abstract

As 6G networks evolve, *inter-provider agreements* become crucial for dynamic resource sharing and network slicing across multiple domains, requiring on-demand capacity provisioning while enabling trustworthy interaction among diverse operators. To address these challenges, we propose a blockchain-based Decentralized Application (DApp) on Ethereum that introduces four smart contracts—organized into a *Preliminary Agreement Phase* and an *Enforcement Phase*—and measures their gas usage, thereby establishing an open marketplace where service providers can list, lease, and enforce resource sharing.

We present an empirical evaluation of how gas price, block size, and transaction count affect transaction processing time on the live Sepolia Ethereum testnet in a realistic setting, focusing on these distinct smart-contract phases with varying computational complexities. We first examine transaction latency as the number of users (batch size) increases, observing median latencies from **12.5 s to 23.9 s** in the *Preliminary Agreement Phase* and **10.9 s to 24.7 s** in the *Enforcement Phase*.

Building on these initial measurements, we perform a comprehensive Kruskal–Wallis test (*p < 0.001*) to compare latency distributions across quintiles of *gas price*, *block size*, and *transaction count*. The post-hoc analyses reveal that high-volume blocks overshadow fee variations when transaction logic is more complex (effect sizes up to **0.43**), whereas gas price exerts a stronger influence when the computation is lighter (effect sizes up to **0.36**). 

Overall, **86%** of transactions finalize within **30 seconds**, underscoring that while designing decentralized applications, there must be a balance between contract complexity and fee strategies.  

The implementation of this work is publicly accessible [online](https://github.com/farhanajaved/InP_DApp_Analysis.git).



![Proposed Framework for Blockchain and Federated Learning in O-RAN](Framework_InP_DApp.png)

## Overview of Smart Contracts

The proposed blockchain-based Decentralized Application (DApp) integrates smart contracts to facilitate inter-provider agreements, ensuring dynamic resource allocation while maintaining trust and enforcement mechanisms. These smart contracts operate in two main phases:

### **1. Preliminary Agreement Phase**
This phase involves the initial service advertisement and selection process:

- **`AddService.sol`**:  
  Allows providers to list their services on the marketplace. Each provider can register up to five services, with gas consumption varying from **162,500** units for the first service to **147,500** for subsequent services.

- **`SelectService.sol`**:  
  Consumers use this contract to choose from available services. The gas consumption ranges between **138,752** and **155,992** units, depending on whether the service was previously selected (*cold vs. warm storage access*).

### **2. Enforcement Phase**
This phase ensures compliance with service agreements and applies penalties for breaches:

- **`RegisterBreach.sol`**:  
  Records contract breaches, with initial transactions consuming around **44,058** gas units, and subsequent executions requiring only **26,958** gas units.

- **`CalculatePenalty.sol`**:  
  Computes penalties based on breach records. The execution requires approximately **49,143** gas units.

### **Gas Consumption Analysis**
Gas costs are a significant consideration in blockchain transactions. The analysis revealed:

- The first transaction in a contract incurs the highest cost due to storage initialization.
- Subsequent transactions use optimized *warm storage*, reducing gas costs.
- Service selection contracts experience varying gas usage depending on storage retrieval type.

This structured approach enables an efficient and transparent **decentralized marketplace** for inter-provider agreements.


## Installation and Running Instructions Using Hardhat

### Prerequisites

- Node.js installed (version 14.x or later)
- A personal Ethereum wallet (e.g., MetaMask)

### Setup

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install dependencies:**
   ```
   npm install
   ```

3. **Create a `.env` file:**
   Add your Ethereum wallet private key and Alchemy/Polygon node URL:
   ```
   PRIVATE_KEY="your-wallet-private-key"
   POLYGON_URL="https://polygon-mumbai.g.alchemy.com/v2/your-api-key"
   ```

### Common Hardhat Commands

- **Compile contracts:**
  ```
  npx hardhat compile
  ```
  This compiles the smart contracts and checks for any syntax errors.

- **Run tests:**
  ```
  npx hardhat test
  ```
  Execute unit tests for the contracts to ensure correct behavior.

- **Deploy contracts:**
  ```
  npx hardhat run scripts/deploy.js --network polygon_mumbai
  ```
  Deploys the smart contracts to the Polygon Mumbai testnet.

- **Interact with deployed contracts:**
  ```
  npx hardhat console --network polygon_mumbai
  ```
  Provides an interactive console to interact with deployed contracts.

- **Verify contract on Etherscan:**
  ```
  npx hardhat verify --network polygon_mumbai DEPLOYED_CONTRACT_ADDRESS
  ```
  Verifies the source code of your deployed contract on the Polygon Etherscan, which is useful for transparency and trust.

### Deployment via Hardhat Ignition

If you want to use Hardhat Ignition for deployment:
```
npx hardhat ignition deploy ./ignition/modules/Lock.js
```
This command deploys modules using Hardhat Ignition, a plugin for advanced deployment scripts.

## Conclusion

This setup not only improves the robustness and efficiency of the O-RAN ecosystem but also enhances data security and user privacy through decentralized technologies. The integration of blockchain allows for a tamper-proof, transparent record-keeping system that significantly boosts the trustworthiness of the federated learning process within telecom networks.
