from app.services.layout_optimizer import LayoutConfig, LayoutValidationError, optimize_parking_layout


def base_config():
    return LayoutConfig(
        slot_type="car",
        slot_width_m=2.5,
        slot_length_m=5.0,
        aisle_width_m=6.0,
        boundary_margin_m=0.0,
        obstacle_margin_m=0.0,
        angles=[0, 90],
        parking_lot_id="LOT1",
        area_id="MAIN",
    )


def test_rectangle_layout_generates_slots():
    result = optimize_parking_layout(
        boundary=[
            {"x": 0, "y": 0},
            {"x": 400, "y": 0},
            {"x": 400, "y": 300},
            {"x": 0, "y": 300},
        ],
        obstacles=[],
        scale_factor=0.1,
        config=base_config(),
    )

    assert result["total"] > 0
    assert result["generated_slots"][0]["status"] == "available"
    assert result["best_angle"] in {0, 90}
    assert len(result["layout_options"]) == 2
    assert result["layout_options"][0]["generated_slots"]


def test_obstacle_reduces_capacity():
    boundary = [
        {"x": 0, "y": 0},
        {"x": 400, "y": 0},
        {"x": 400, "y": 300},
        {"x": 0, "y": 300},
    ]
    no_obstacle = optimize_parking_layout(
        boundary=boundary,
        obstacles=[],
        scale_factor=0.1,
        config=base_config(),
    )
    with_obstacle = optimize_parking_layout(
        boundary=boundary,
        obstacles=[[
            {"x": 150, "y": 100},
            {"x": 250, "y": 100},
            {"x": 250, "y": 200},
            {"x": 150, "y": 200},
        ]],
        scale_factor=0.1,
        config=base_config(),
    )

    assert with_obstacle["total"] < no_obstacle["total"]


def test_invalid_scale_rejected():
    try:
        optimize_parking_layout(
            boundary=[
                {"x": 0, "y": 0},
                {"x": 100, "y": 0},
                {"x": 100, "y": 100},
            ],
            obstacles=[],
            scale_factor=0,
            config=base_config(),
        )
    except LayoutValidationError:
        return

    raise AssertionError("Expected invalid scale to be rejected")
