// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ServiceSelection {
    struct Service {
        uint256 serviceId;
        string location;
        uint256 cost;
    }

    struct Provider {
        address providerAddress;
        mapping(uint256 => Service) services;
        uint256[] serviceIds;
    }

    struct Selection {
        address consumer;
        address provider;
        uint256 serviceId;
    }

    mapping(address => Provider) public providers;
    address[] public providerAddresses;
    Selection[] public selections;

    event ServiceAdded(address indexed provider, uint256 serviceId, string location, uint256 cost);
    event ServiceSelected(address indexed consumer, address indexed provider, uint256 serviceId);

    function addService(uint256 serviceId, string memory location, uint256 cost) public {
        Provider storage provider = providers[msg.sender];
        if (provider.providerAddress == address(0)) {
            provider.providerAddress = msg.sender;
            providerAddresses.push(msg.sender);
        }
        
        provider.services[serviceId] = Service(serviceId, location, cost);
        provider.serviceIds.push(serviceId);
        emit ServiceAdded(msg.sender, serviceId, location, cost);
    }

    function getProviders() public view returns (address[] memory) {
        return providerAddresses;
    }

    function getProviderServices(address provider) public view returns (Service[] memory) {
        Provider storage p = providers[provider];
        require(p.providerAddress != address(0), "Provider not found");

        Service[] memory services = new Service[](p.serviceIds.length);
        for (uint256 i = 0; i < p.serviceIds.length; i++) {
            services[i] = p.services[p.serviceIds[i]];
        }
        return services;
    }

    function selectService(address provider, uint256 serviceId) public {
        Provider storage p = providers[provider];
        require(p.providerAddress != address(0), "Provider not found");

        Service storage service = p.services[serviceId];
        require(service.serviceId != 0, "Service not found");

        selections.push(Selection(msg.sender, provider, serviceId));
        emit ServiceSelected(msg.sender, provider, serviceId);
    }

    function getSelections() public view returns (Selection[] memory) {
        return selections;
    }
}
