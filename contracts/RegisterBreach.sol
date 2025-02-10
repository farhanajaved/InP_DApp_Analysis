// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @dev Minimal interface for CalculatePenalty so that RegisterBreach can call it.
 */
interface ICalculatePenalty {
    function calculatePenalty(address user) external returns (uint256);
}

contract RegisterBreach {
    // Mapping to track the number of breaches per user.
    mapping(address => uint256) public breaches;

    // The address of the deployed CalculatePenalty contract.
    address public calculatePenaltyContract;

    // Event emitted when a breach is registered.
    event BreachRegistered(address indexed user, uint256 breachCount);

    /**
     * @dev Sets the address of the CalculatePenalty contract.
     * In a production environment, you might restrict who can set this.
     */
    function setCalculatePenaltyContract(address _calcPenaltyAddress) public {
        calculatePenaltyContract = _calcPenaltyAddress;
    }

    /**
     * @dev Registers a breach and, if the threshold is reached,
     * calls the penalty calculation on the CalculatePenalty contract.
     */
    function registerBreach(uint256 numBreaches) public {
        breaches[msg.sender] += numBreaches;
        emit BreachRegistered(msg.sender, breaches[msg.sender]);

        // Define a breach threshold; adjust as needed.
        uint256 maxBreaches = 10;
        if (breaches[msg.sender] >= maxBreaches) {
            // Call calculatePenalty on the CalculatePenalty contract.
            // This uses the interface defined above.
            ICalculatePenalty(calculatePenaltyContract).calculatePenalty(msg.sender);
        }
    }
}
