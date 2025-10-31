"""Tests for API endpoints."""
import pytest
from src.db.models import RequestState, ContractState


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_publication(client, sample_publication_data):
    """Test creating a publication."""
    response = client.post("/publications", json=sample_publication_data)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == sample_publication_data["title"]
    assert data["description"] == sample_publication_data["description"]
    assert "id" in data
    assert "owner_id" in data


def test_list_publications(client, sample_publication_data):
    """Test listing publications."""
    # Create a publication first
    client.post("/publications", json=sample_publication_data)
    
    response = client.get("/publications")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_get_publication(client, sample_publication_data):
    """Test getting a specific publication."""
    # Create a publication
    create_response = client.post("/publications", json=sample_publication_data)
    pub_id = create_response.json()["id"]
    
    # Get the publication
    response = client.get(f"/publications/{pub_id}")
    assert response.status_code == 200
    assert response.json()["id"] == pub_id


def test_get_nonexistent_publication(client):
    """Test getting a publication that doesn't exist."""
    response = client.get("/publications/nonexistent-id")
    assert response.status_code == 404


def test_create_request(client, sample_request_data):
    """Test creating a request."""
    response = client.post("/requests", json=sample_request_data)
    assert response.status_code == 201
    data = response.json()
    assert data["subject"] == sample_request_data["subject"]
    assert data["state"] == "open"
    assert "id" in data


def test_create_request_with_publication(client, sample_publication_data, sample_request_data):
    """Test creating a request linked to a publication."""
    # Create a publication first
    pub_response = client.post("/publications", json=sample_publication_data)
    pub_id = pub_response.json()["id"]
    
    # Create a request for this publication
    sample_request_data["publication_id"] = pub_id
    response = client.post("/requests", json=sample_request_data)
    assert response.status_code == 201
    assert response.json()["publication_id"] == pub_id


def test_create_request_with_invalid_publication(client, sample_request_data):
    """Test creating a request with an invalid publication ID."""
    sample_request_data["publication_id"] = "invalid-id"
    response = client.post("/requests", json=sample_request_data)
    assert response.status_code == 404


def test_list_requests(client, sample_request_data):
    """Test listing requests."""
    # Create a request first
    client.post("/requests", json=sample_request_data)
    
    response = client.get("/requests")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_create_contract(client, sample_request_data, sample_contract_data):
    """Test creating a contract from a request."""
    # Create a request first
    req_response = client.post("/requests", json=sample_request_data)
    req_id = req_response.json()["id"]
    
    # Create a contract
    sample_contract_data["request_id"] = req_id
    response = client.post("/contracts", json=sample_contract_data)
    assert response.status_code == 201
    data = response.json()
    assert data["request_id"] == req_id
    assert data["state"] == "active"
    assert data["signature_method"] == "implicit_acceptance"
    assert data["terms"] == sample_contract_data["terms"]


def test_create_contract_updates_request_state(client, sample_request_data, sample_contract_data):
    """Test that creating a contract updates the request state."""
    # Create a request
    req_response = client.post("/requests", json=sample_request_data)
    req_id = req_response.json()["id"]
    
    # Create a contract
    sample_contract_data["request_id"] = req_id
    client.post("/contracts", json=sample_contract_data)
    
    # Check request state
    req_check = client.get(f"/requests/{req_id}")
    assert req_check.json()["state"] == "contracted"


def test_create_contract_with_invalid_request(client, sample_contract_data):
    """Test creating a contract with an invalid request ID."""
    sample_contract_data["request_id"] = "invalid-id"
    response = client.post("/contracts", json=sample_contract_data)
    assert response.status_code == 404


def test_list_contracts(client, sample_request_data, sample_contract_data):
    """Test listing contracts."""
    # Create a request and contract
    req_response = client.post("/requests", json=sample_request_data)
    sample_contract_data["request_id"] = req_response.json()["id"]
    client.post("/contracts", json=sample_contract_data)
    
    response = client.get("/contracts")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_create_transfer(
    client, sample_request_data, sample_contract_data, sample_transfer_data, mock_s3_service
):
    """Test creating a transfer."""
    # Create request and contract
    req_response = client.post("/requests", json=sample_request_data)
    sample_contract_data["request_id"] = req_response.json()["id"]
    contract_response = client.post("/contracts", json=sample_contract_data)
    contract_id = contract_response.json()["id"]
    
    # Create transfer
    sample_transfer_data["contract_id"] = contract_id
    response = client.post("/transfers", json=sample_transfer_data)
    assert response.status_code == 201
    data = response.json()
    assert data["contract_id"] == contract_id
    assert data["destination"] == sample_transfer_data["destination"]
    assert "presigned_url" in data
    assert data["state"] == "in_progress"


def test_create_transfer_with_invalid_contract(client, sample_transfer_data, mock_s3_service):
    """Test creating a transfer with an invalid contract ID."""
    sample_transfer_data["contract_id"] = "invalid-id"
    response = client.post("/transfers", json=sample_transfer_data)
    assert response.status_code == 404


def test_complete_transfer(
    client, sample_request_data, sample_contract_data, sample_transfer_data, mock_s3_service
):
    """Test completing a transfer."""
    # Create request, contract, and transfer
    req_response = client.post("/requests", json=sample_request_data)
    sample_contract_data["request_id"] = req_response.json()["id"]
    contract_response = client.post("/contracts", json=sample_contract_data)
    sample_transfer_data["contract_id"] = contract_response.json()["id"]
    transfer_response = client.post("/transfers", json=sample_transfer_data)
    transfer_id = transfer_response.json()["id"]
    
    # Complete the transfer
    response = client.post(f"/transfers/{transfer_id}/complete")
    assert response.status_code == 200
    
    # Verify transfer is completed
    transfer_check = client.get(f"/transfers/{transfer_id}")
    assert transfer_check.json()["state"] == "completed"


def test_list_transfers(
    client, sample_request_data, sample_contract_data, sample_transfer_data, mock_s3_service
):
    """Test listing transfers."""
    # Create request, contract, and transfer
    req_response = client.post("/requests", json=sample_request_data)
    sample_contract_data["request_id"] = req_response.json()["id"]
    contract_response = client.post("/contracts", json=sample_contract_data)
    sample_transfer_data["contract_id"] = contract_response.json()["id"]
    client.post("/transfers", json=sample_transfer_data)
    
    response = client.get("/transfers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_sync_catalog(client, monkeypatch):
    """Test catalog synchronization."""
    # Mock the sync function to return test data
    def mock_sync():
        return [
            {"title": "Dataset 1", "description": "Test 1", "metadata": {}},
            {"title": "Dataset 2", "description": "Test 2", "metadata": {}},
        ]
    
    from src import catalog
    monkeypatch.setattr(catalog, "sync_openmetadata_catalog", mock_sync)
    
    response = client.post("/sync/catalog")
    assert response.status_code == 200
    data = response.json()
    assert data["imported"] == 2


def test_audit_logs(client, sample_publication_data):
    """Test retrieving audit logs."""
    # Create a publication to generate audit logs
    client.post("/publications", json=sample_publication_data)
    
    response = client.get("/audit-logs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert "event_type" in data[0]
    assert "payload" in data[0]


def test_full_workflow(
    client,
    sample_publication_data,
    sample_request_data,
    sample_contract_data,
    sample_transfer_data,
    mock_s3_service,
):
    """Test complete workflow: publication -> request -> contract -> transfer."""
    # 1. Create publication
    pub_response = client.post("/publications", json=sample_publication_data)
    assert pub_response.status_code == 201
    pub_id = pub_response.json()["id"]
    
    # 2. Create request for publication
    sample_request_data["publication_id"] = pub_id
    req_response = client.post("/requests", json=sample_request_data)
    assert req_response.status_code == 201
    req_id = req_response.json()["id"]
    
    # 3. Create contract from request
    sample_contract_data["request_id"] = req_id
    contract_response = client.post("/contracts", json=sample_contract_data)
    assert contract_response.status_code == 201
    contract_id = contract_response.json()["id"]
    
    # 4. Create transfer from contract
    sample_transfer_data["contract_id"] = contract_id
    transfer_response = client.post("/transfers", json=sample_transfer_data)
    assert transfer_response.status_code == 201
    transfer_id = transfer_response.json()["id"]
    
    # 5. Complete transfer
    complete_response = client.post(f"/transfers/{transfer_id}/complete")
    assert complete_response.status_code == 200
    
    # Verify final states
    final_request = client.get(f"/requests/{req_id}").json()
    assert final_request["state"] == "contracted"
    
    final_transfer = client.get(f"/transfers/{transfer_id}").json()
    assert final_transfer["state"] == "completed"
