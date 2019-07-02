"""Unit tests for the REST API module."""
import json
import os

valid_paylod = {
    "value": 26.0,
    "pid": 123,
    "endpoint": "api_v1.test__slashless",
    "request_method": "GET",
    "status_code": 200
}

invalid_payload_assert = {
    "pid": 1236,
    "hostname": "localhost1"
}

invalid_payload_type = {
    "value": 26,
    "endpoint": "api_v1.test__slashless",
    "request_method": "GET",
    "status_code": 200
}


def api_route_for(route):
    """Construct an URL to the endpoint for given route."""
    return '/api/v1/' + route


def get_json_from_response(response):
    """Decode JSON from response."""
    return json.loads(response.data.decode('utf8'))


def test_readiness(client):
    """Test the readiness endpoint."""
    response = client.get(api_route_for("readiness"))
    assert response.status_code == 200
    json_data = get_json_from_response(response)
    assert json_data == {}


def test_liveness(client):
    """Test the liveness endpoint."""
    response = client.get(api_route_for("liveness"))
    assert response.status_code == 200
    json_data = get_json_from_response(response)
    assert json_data == {}


def test_metrics_collection_invalid_payload(client):
    """Test the metrics collection endpoint."""
    response = client.post(api_route_for("prometheus"), json=invalid_payload_assert)
    assert response.status_code == 400
    json_data = get_json_from_response(response)
    assert "message" in json_data
    assert json_data["message"] == "Make sure payload is valid and contains all " \
                                   "the mandatory fields."


def test_metrics_collection_invalid_payload2(client):
    """Test the metrics collection endpoint."""
    response = client.post(api_route_for("prometheus"), json=invalid_payload_type)
    assert response.status_code == 400
    json_data = get_json_from_response(response)
    assert "message" in json_data
    assert json_data["message"] == "Make sure payload is valid and contains all " \
                                   "the mandatory fields."


def test_metrics_collection_valid_payload(client):
    """Test the metrics collection endpoint."""
    response = client.post(api_route_for("prometheus"), json=valid_paylod)
    assert response.status_code == 200
    json_data = get_json_from_response(response)
    assert "message" in json_data
    assert json_data["message"] == "success"


def test_metrics_exposition(client):
    """Test the metrics exposition endpoint."""
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.data is not None
    # Remove the files created by metrics collection
    os.remove("tests/logs/counter_" + str(os.getpid()) + ".db")
    os.remove("tests/logs/histogram_" + str(os.getpid()) + ".db")
