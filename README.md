# AzureGraphQL
GraphQL Wrapper for the Azure management API

Example query

```graphql
{ VirtualMachines(subscriptionId: "b9334351-cec8-405d-8358-51846fa2a3ab") {
  name
  nic {
    name
    ip
    publicIP {
      name
      ip
    }
  }
}}
````

Header

```graphql
{"Authorization":"Bearer xxxxxxxxxxxxxxxx"}
```
