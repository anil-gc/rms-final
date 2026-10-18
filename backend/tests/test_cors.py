from django.test import override_settings
from django.urls import reverse


@override_settings(CORS_ALLOWED_ORIGINS=["https://frontend.example.test"])
def test_allowed_origin_gets_cors_header(api_client):
    response = api_client.get(reverse("v1:health"), HTTP_ORIGIN="https://frontend.example.test")
    assert response["Access-Control-Allow-Origin"] == "https://frontend.example.test"
    assert "Access-Control-Allow-Credentials" not in response


@override_settings(CORS_ALLOWED_ORIGINS=["https://frontend.example.test"])
def test_unlisted_origin_gets_no_cors_grant(api_client):
    response = api_client.get(reverse("v1:health"), HTTP_ORIGIN="https://untrusted.example.test")
    assert "Access-Control-Allow-Origin" not in response


@override_settings(CORS_ALLOWED_ORIGINS=["https://frontend.example.test"])
def test_browser_preflight(api_client):
    response = api_client.options(
        reverse("v1:health"),
        HTTP_ORIGIN="https://frontend.example.test",
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type",
    )
    assert response.status_code == 200
    assert response["Access-Control-Allow-Origin"] == "https://frontend.example.test"
    assert "GET" in response["Access-Control-Allow-Methods"]
