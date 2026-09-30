from app.route_completion import RouteCompletionResult


def test_route_completion_result_shape() -> None:
    result = RouteCompletionResult(
        added=1,
        already_visited=2,
        unavailable=3,
    )

    assert result.added == 1
    assert result.already_visited == 2
    assert result.unavailable == 3
