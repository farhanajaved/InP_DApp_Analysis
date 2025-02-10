// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract AddService {
    struct Service {
        address provider;
        string serviceId;
        string location;
        uint256 cost;
    }

    Service[] public services;  // Global array to store all services
    mapping(address => uint256[]) public providerServices;  // Map each provider to an array of service indices

    // Function to add a new service
    function addService(string memory serviceId, string memory location, uint256 cost) public {
        services.push(Service(msg.sender, serviceId, location, cost));
        providerServices[msg.sender].push(services.length - 1);
    }

    // Function to retrieve service by global index
    function getService(uint256 index) public view returns (Service memory) {
        require(index < services.length, "Service index out of range");
        return services[index];
    }

    // Function to get all service indices for a specific provider
    function getProviderServices(address provider) public view returns (uint256[] memory) {
        return providerServices[provider];
    }

    // Function to get the number of services added by a provider
    function getServiceCount(address provider) public view returns (uint) {
        return providerServices[provider].length;
    }
}
