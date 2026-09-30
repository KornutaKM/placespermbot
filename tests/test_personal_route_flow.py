from app.handlers.main import LOCATION_REQUEST_STATES, PersonalRouteFlow


def test_personal_route_location_request_is_globally_cancelable() -> None:
    assert PersonalRouteFlow.waiting_location.state in LOCATION_REQUEST_STATES
    assert PersonalRouteFlow.waiting_duration.state not in LOCATION_REQUEST_STATES
