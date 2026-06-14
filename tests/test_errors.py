from sesamehr import SesameApiError, SesameConnectionError, SesameError


def test_nested_error_message():
    error = SesameApiError(422, {"error": {"message": "Validation failed"}})
    assert error.message == "Validation failed"
    assert error.status == 422


def test_flat_message_priority():
    assert SesameApiError(400, {"message": "flat"}).message == "flat"
    assert SesameApiError(400, {"error": "broken"}).message == "broken"
    assert SesameApiError(400, {"error_description": "oauth-ish"}).message == "oauth-ish"


def test_message_priority_order():
    error = SesameApiError(400, {"message": "first", "error": "second"})
    assert error.message == "first"


def test_fallback_message_on_non_object_body():
    assert SesameApiError(500, None).message == "Sesame API error: HTTP 500"
    assert SesameApiError(502, "plain text").message == "Sesame API error: HTTP 502"


def test_array_messages_flattened():
    error = SesameApiError(422, {"message": ["one", ["two", "three"], None]})
    assert error.message == "one, two, three"


def test_errors_list_extracted():
    error = SesameApiError(422, {"error": {"message": "bad", "errors": ["a", "b"]}})
    assert error.errors == ["a", "b"]

    flat = SesameApiError(422, {"message": "bad", "errors": [{"field": "x"}]})
    assert flat.errors == [{"field": "x"}]

    none = SesameApiError(422, {"message": "bad"})
    assert none.errors == []


def test_connection_error_is_sesame_error():
    error = SesameConnectionError("boom")
    assert isinstance(error, SesameError)
    assert str(error) == "Connection failed: boom"
