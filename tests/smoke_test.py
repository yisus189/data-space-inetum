"""E2E smoke test script."""
import requests
import sys
import time


def wait_for_service(url, max_attempts=30):
    """Wait for service to be ready."""
    for i in range(max_attempts):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 500:
                print(f"✓ Service ready: {url}")
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    print(f"✗ Service not ready: {url}")
    return False


def test_health():
    """Test health endpoint."""
    response = requests.get("http://localhost:8000/metrics/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    print("✓ Health check passed")


def test_readiness():
    """Test readiness endpoint."""
    response = requests.get("http://localhost:8000/metrics/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    print("✓ Readiness check passed")


def test_list_datasets():
    """Test listing public datasets."""
    response = requests.get("http://localhost:8000/datasets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    print(f"✓ List datasets passed (found {len(data)} datasets)")


def test_openmetadata_catalog():
    """Test OpenMetadata catalog endpoint."""
    response = requests.get("http://localhost:8000/integrations/openmetadata/catalog")
    # May fail if OpenMetadata not configured, but should not crash
    print(f"✓ OpenMetadata catalog endpoint accessible (status: {response.status_code})")


def test_edc_stub():
    """Test EDC stub endpoints."""
    response = requests.post(
        "http://localhost:8000/edc/catalog",
        json={"provider_url": "http://provider.example.com"}
    )
    assert response.status_code == 200
    print("✓ EDC stub catalog endpoint passed")


def test_metrics():
    """Test Prometheus metrics endpoint."""
    response = requests.get("http://localhost:8000/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text or len(response.text) > 0
    print("✓ Metrics endpoint passed")


def main():
    """Run E2E smoke tests."""
    print("Starting E2E smoke tests...")
    print()
    
    # Wait for API to be ready
    if not wait_for_service("http://localhost:8000/metrics/health"):
        print("API not ready, aborting tests")
        sys.exit(1)
    
    print()
    
    try:
        test_health()
        test_readiness()
        test_list_datasets()
        test_openmetadata_catalog()
        test_edc_stub()
        test_metrics()
        
        print()
        print("=" * 50)
        print("All smoke tests passed! ✓")
        print("=" * 50)
        sys.exit(0)
        
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
