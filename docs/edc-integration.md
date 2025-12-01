# EDC (Eclipse Dataspace Connector) Integration

This document describes how to integrate the Data Space with the Eclipse Dataspace Connector (EDC) for managed data transfers.

## Overview

The EDC provides IDS-compliant data transfer capabilities including:
- Contract negotiation
- Policy enforcement
- Secure data transfer protocols

## Current Implementation

The current implementation includes a **stub** for EDC integration at `/integrations/edc/transfer`. This endpoint:
1. Accepts a dataset ID and consumer ID
2. Returns a stub response indicating EDC is not fully configured

## Production Configuration

To enable full EDC integration:

### 1. Deploy EDC Connector

Deploy the EDC control and data planes. Recommended configuration:

```yaml
# docker-compose.edc.yml
services:
  edc-control-plane:
    image: ghcr.io/eclipse-edc/connector:latest
    ports:
      - "19193:19193"  # Management API
      - "19191:19191"  # Protocol API
    environment:
      EDC_CONNECTOR_NAME: dataspace-edc
      EDC_IDENTITY_DID_URL: did:web:dataspace.example
    volumes:
      - ./config/edc:/config

  edc-data-plane:
    image: ghcr.io/eclipse-edc/data-plane:latest
    ports:
      - "19291:19291"
    environment:
      EDC_CONNECTOR_NAME: dataspace-edc-data
```

### 2. Environment Variables

Add to your `.env`:

```env
EDC_CONTROL_PLANE_URL=http://localhost:19193/management
EDC_API_KEY=your-edc-api-key
EDC_CONNECTOR_ID=dataspace-edc
```

### 3. Code Changes

Update `src/integrations/router.py` to make actual EDC API calls:

```python
import httpx

EDC_URL = os.getenv("EDC_CONTROL_PLANE_URL")
EDC_API_KEY = os.getenv("EDC_API_KEY")

async def create_edc_contract_negotiation(dataset_id: str, consumer_id: str):
    async with httpx.AsyncClient() as client:
        # Create contract definition
        contract_def = {
            "id": f"contract-{dataset_id}",
            "accessPolicyId": "default-access",
            "contractPolicyId": "default-contract",
            "assetsSelector": {
                "operandLeft": "asset:prop:id",
                "operator": "=",
                "operandRight": dataset_id
            }
        }
        
        response = await client.post(
            f"{EDC_URL}/v2/contractdefinitions",
            json=contract_def,
            headers={"X-Api-Key": EDC_API_KEY}
        )
        return response.json()
```

### 4. Asset Registration

Register datasets as EDC assets when published:

```python
async def register_edc_asset(dataset: Dataset, storage_url: str):
    asset = {
        "id": str(dataset.id),
        "properties": {
            "name": dataset.title,
            "description": dataset.description,
            "contenttype": "application/octet-stream"
        },
        "dataAddress": {
            "type": "HttpData",
            "baseUrl": storage_url
        }
    }
    # POST to EDC /v2/assets
```

## ODRL Policy Mapping

The Data Space ODRL policies can be mapped to EDC policies:

| Data Space Policy | EDC Policy |
|-------------------|------------|
| permission.action = use | odrl:use permission |
| constraint.purpose = research | constraint with research purpose |
| prohibition.action = distribute | prohibition rule |

## Testing EDC Integration

1. Start EDC connectors
2. Create a dataset and publish it
3. Use the EDC management API to verify asset registration
4. Initiate a contract negotiation
5. Monitor transfer status

## Resources

- [EDC Documentation](https://eclipse-edc.github.io/docs/)
- [EDC Samples](https://github.com/eclipse-edc/Samples)
- [IDS Reference Architecture](https://internationaldataspaces.org/publications/)
