// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// Import the RegisterBreach contract so we can query its breach data.
import "./RegisterBreach.sol";

contract CalculatePenalty {
    // Mapping to store calculated penalties per user.
    mapping(address => uint256) public penalties;

    // Reference to the RegisterBreach contract.
    RegisterBreach public registerBreachContract;

    // Event emitted when a penalty is calculated.
    event PenaltyCalculated(address indexed user, uint256 penalty);

    /**
     * @dev Constructor sets the address of the deployed RegisterBreach contract.
     */
    constructor(address _registerBreachContract) {
        registerBreachContract = RegisterBreach(_registerBreachContract);
    }

    /**
     * @dev Calculates the penalty for a user based on their breach count.
     * This function is intended to be called only by the RegisterBreach contract.
     */
    function calculatePenalty(address user) public returns (uint256) {
        // Ensure only the RegisterBreach contract can trigger this function.
        require(
            msg.sender == address(registerBreachContract),
            "Only RegisterBreach can call calculatePenalty"
        );

        // Retrieve the breach count for the user.
        uint256 breachCount = registerBreachContract.breaches(user);
        require(breachCount < 10**18, "Breach count is too high, it may cause overflow");

        // A simple formula to calculate the penalty.
        uint256 penalty = breachCount * (breachCount + 1) * (100 - breachCount) / 100;
        penalties[user] = penalty;

        emit PenaltyCalculated(user, penalty);
        return penalty;
    }
}
