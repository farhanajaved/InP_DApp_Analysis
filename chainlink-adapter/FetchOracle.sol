pragma solidity ^0.6.7;

import "@chainlink/contracts/src/v0.6/ChainlinkClient.sol";

contract MockDataConsumer is ChainlinkClient {
    uint256 public retrievedValue;
    address private oracle;
    bytes32 private jobId;
    uint256 private fee;
    
    constructor() public {
        // Sepolia Testnet details:
        setChainlinkToken(0x779877A7B0D9E8603169DdbD7836e478b4624789); // Link Token for Sepolia
        oracle = 0x6090149792dAAeE9D1D568c9f9a6F6B46AA29eFD; // Chainlink DevRel Oracle for Sepolia
        jobId = stringToBytes32("7223acbd01654282865b678924126013"); // Job ID
        fee = 0.1 * 10**18; // 0.1 LINK
    }
    
    function requestData() external returns (bytes32 requestId) {
        Chainlink.Request memory request = buildChainlinkRequest(jobId, address(this), this.fulfill.selector);
        
        // Assuming you are testing locally and your Chainlink node is configured to fetch data from localhost:
        request.add("get", "http://localhost:8080/fetch-data"); // Replace 'fetch-data' with your adapter's endpoint if it's different.
        request.add("path", "data.value");
        return sendChainlinkRequestTo(oracle, request, fee);
    }

    function fulfill(bytes32 _requestId, uint256 _value) external recordChainlinkFulfillment(_requestId) {
        retrievedValue = _value;
    }

    function stringToBytes32(string memory source) public pure returns (bytes32 result) {
        bytes memory tempEmptyStringTest = bytes(source);
        if (tempEmptyStringTest.length == 0) {
            return 0x0;
        }
        assembly {
            result := mload(add(source, 32))
        }
    }
}
