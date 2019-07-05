# GraphQL Wrapper for the Azure management API

_Current state is proof of concept._

## Getting started

Python must be installed and some extra modules (I believe the following should cover it)

```
pip install ariadne
pip install aiohttp
pip install requests
pip install uvicorn
```

Then simply run it

```
python '.\path\to\poc.py'
```

and visit [127.0.0.1:8000/](http://127.0.0.1:8000/) in your favorite browser.

In the bottom left part of the editor the Bearer token must be entered in the following form:
```graphql
{"Authorization":"Bearer thisisaverylongonethatswhatshesaid"}
```

This is an easy way to get the [bearer token in 2 minutes](https://blog.jongallant.com/2017/11/azure-rest-apis-postman/) and just general nice way to get Postman quickly setup to work with the Azure API.

## Example

This shows the speed at which all of the data is gathered. The equivalent of 12 REST API calls. Some of which could be done asynchronously, but GraphQL does that and handles any dependencies at the same time.

The code is just 200 lines of which the first 80 is imports and type definitions.

![Example](/media/example.gif)

## Example

Query to get virtual machines and *lots and lots* of nested properties that would require numerous calls to the Azure REST API:

```graphql
{ VirtualMachines(subscriptionId: "xxx-xxxx-xxx") {
  name
  size
  os
  location
  nic {
    name
    ip
    networkSecurityGroup {
      name
      rules {
        name
        protocol
        access
      }
    }
    subnet {
      name
      addressPrefix
    }
    publicIP {      
      ip
    }
  }
}}
````

Result:

```graphql
{
  "data": {
    "VirtualMachines": [
      {
        "name": "certbot-01",
        "size": "Standard_B1ms",
        "os": "Linux",
        "location": "westeurope",
        "nic": {
          "name": "certbot-01810",
          "ip": "172.18.0.4",
          "networkSecurityGroup": {
            "name": "certbot-01-nsg",
            "rules": [
              {
                "name": "SSH",
                "protocol": "TCP",
                "access": "Allow"
              },
              {
                "name": "AllowHttpInbound",
                "protocol": "TCP",
                "access": "Allow"
              },
              {
                "name": "AllowHttpsInbound",
                "protocol": "TCP",
                "access": "Allow"
              }
            ]
          },
          "subnet": {
            "name": "default",
            "addressPrefix": "172.18.0.0/24"
          },
          "publicIP": {
            "ip": "40.113.144.28"
          }
        }
      },
      {
        "name": "vm-pihole",
        "size": "Standard_B1s",
        "os": "Linux",
        "location": "westeurope",
        "nic": {
          "name": "vm-pihole342",
          "ip": "10.0.0.4",
          "networkSecurityGroup": null,
          "subnet": {
            "name": "default",
            "addressPrefix": "10.0.0.0/28"
          },
          "publicIP": {
            "ip": "52.233.137.218"
          }
        }
      },
      {
        "name": "Win10-WD002",
        "size": "Standard_DS3_v2",
        "os": "Windows",
        "location": "westeurope",
        "nic": {
          "name": "win10-wd002",
          "ip": "10.0.0.7",
          "networkSecurityGroup": null,
          "subnet": {
            "name": "DtlwdlabSubnet",
            "addressPrefix": "10.0.0.0/20"
          },
          "publicIP": {
            "ip": null
          }
        }
      }
    ]
  }
}
```