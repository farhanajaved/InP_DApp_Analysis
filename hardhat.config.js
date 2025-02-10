require("dotenv").config();
require("@nomiclabs/hardhat-ethers");

module.exports = {
  solidity: "0.8.24",
  networks: {
    polygon: {
      url: process.env.API_URL,
      accounts: [process.env.PRIVATE_KEY].filter(Boolean)
    }
  }
};

