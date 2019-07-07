function Get-AzgVirtualMachine {
    [CmdletBinding()]
    param (
        [switch]$IncludeNetwork,
        [switch]$Raw
    )
    
    begin {
        Import-Module ".\src\lib\core.ps1"
        $SubscriptionId = (Get-AzContext).Subscription.ID

        $qnic = @"
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
"@

        $Body = @{
            operationName = "getVirtualMachines"
            variables = @{
                subscriptionId = $SubscriptionId
            }
            query = "query getVirtualMachines(`$subscriptionId: String!) {
                VirtualMachines(subscriptionId: `$subscriptionId) {
                    name
                    size
                    os
                    location
                    $(
                    if($IncludeNetwork.IsPresent)
                    {
                        $qnic
                    }
                    )
                }
            }"
        } | ConvertTo-Json

        $uri = 'http://127.0.0.1:8000'
        $Headers = @{
            Authorization = ('Bearer {0}' -f (Get-AzCachedAccessToken))
            'content-type' = 'application/json'
        }        
    }
    
    process {
        $Data = $Response = $null
        try {
            $Response = Invoke-WebRequest -UseBasicParsing -Uri $uri -Method Post -Headers $Headers -Body $Body -TimeoutSec 5 -ErrorAction Stop
        }
        catch {
            throw $_
        }

        $Data = ($Response.Content | ConvertFrom-Json).data
    }
    
    end {
        if($Raw.IsPresent)
        {
            $Data.VirtualMachines
        }
        else 
        {
            # TODO: only include relevant properties
            foreach ($VM in $Data.VirtualMachines) {
                $VM | Select-Object -Property name, size, os, location, `
                @{Name = 'ip'; Expression={$VM.nic.ip}}
            }            
        }
    }
}