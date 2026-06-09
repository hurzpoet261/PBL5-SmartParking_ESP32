"""
Parking layout optimizer based on polygon geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import floor
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from shapely.affinity import rotate
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep
from shapely.validation import explain_validity


class LayoutValidationError(ValueError):
    """Raised when layout input cannot produce a valid geometry."""


@dataclass(frozen=True)
class LayoutConfig:
    slot_type: str
    slot_width_m: float
    slot_length_m: float
    aisle_width_m: float
    boundary_margin_m: float
    obstacle_margin_m: float
    angles: Sequence[float]
    parking_lot_id: str
    area_id: str


def _point_tuple(point: Dict[str, Any]) -> Tuple[float, float]:
    try:
        return float(point["x"]), float(point["y"])
    except (KeyError, TypeError, ValueError) as exc:
        raise LayoutValidationError("Each polygon point must contain numeric x and y") from exc


def _build_polygon(points: Sequence[Dict[str, Any]], name: str) -> Polygon:
    if len(points or []) < 3:
        raise LayoutValidationError(f"{name} must contain at least 3 points")

    polygon = Polygon([_point_tuple(point) for point in points])
    if polygon.is_empty or polygon.area <= 0:
        raise LayoutValidationError(f"{name} area must be greater than 0")
    if not polygon.is_valid:
        raise LayoutValidationError(f"{name} is invalid: {explain_validity(polygon)}")
    return polygon


def _row_label(index: int) -> str:
    value = index + 1
    label = ""
    while value:
        value, rem = divmod(value - 1, 26)
        label = chr(65 + rem) + label
    return label


def _round_point(value: float) -> float:
    return round(float(value), 3)


def _polygon_points(polygon: Polygon) -> List[Dict[str, float]]:
    return [{"x": _round_point(x), "y": _round_point(y)} for x, y in list(polygon.exterior.coords)[:-1]]


def _slot_code(parking_lot_id: str, row_index: int, sequence: int) -> str:
    lot = (parking_lot_id or "LOT1").upper()
    return f"{lot}-{_row_label(row_index)}-{sequence:03d}"


def _option_id(angle: float, pattern: Optional[str]) -> str:
    angle_text = str(angle).replace("-", "neg").replace(".", "p")
    return f"angle_{angle_text}_{pattern or 'none'}"


def _generate_axis_rows(
    *,
    min_y: float,
    max_y: float,
    slot_length_px: float,
    aisle_width_px: float,
    offset_y: float,
    pattern: str,
) -> Iterable[float]:
    if pattern == "double":
        block_height = slot_length_px * 2 + aisle_width_px
        y = min_y - slot_length_px + offset_y
        while y + slot_length_px <= max_y + slot_length_px:
            yield y
            second_row = y + slot_length_px + aisle_width_px
            if second_row + slot_length_px <= max_y + slot_length_px:
                yield second_row
            y += block_height
        return

    row_step = slot_length_px + aisle_width_px
    y = min_y - slot_length_px + offset_y
    while y + slot_length_px <= max_y + slot_length_px:
        yield y
        y += row_step


def _candidate_for_angle(
    *,
    usable_area: Polygon,
    angle: float,
    origin: Tuple[float, float],
    config: LayoutConfig,
    scale_factor: float,
    offset_x_ratio: float,
    offset_y_ratio: float,
    pattern: str,
    max_slots: int,
) -> Dict[str, Any]:
    slot_width_px = config.slot_width_m / scale_factor
    slot_length_px = config.slot_length_m / scale_factor
    aisle_width_px = config.aisle_width_m / scale_factor

    rotated_area = rotate(usable_area, -angle, origin=origin, use_radians=False)
    check_area = rotated_area.buffer(0.01)
    prepared_area = prep(check_area)
    min_x, min_y, max_x, max_y = rotated_area.bounds

    slots: List[Dict[str, Any]] = []
    row_index = 0
    global_sequence = 1

    x_start = min_x - slot_width_px + offset_x_ratio * slot_width_px
    y_offset = offset_y_ratio * max(slot_length_px, 1)

    for y in _generate_axis_rows(
        min_y=min_y,
        max_y=max_y,
        slot_length_px=slot_length_px,
        aisle_width_px=aisle_width_px,
        offset_y=y_offset,
        pattern=pattern,
    ):
        col_index = 0
        row_has_slot = False
        x = x_start
        while x + slot_width_px <= max_x + slot_width_px:
            rect = box(x, y, x + slot_width_px, y + slot_length_px)
            if prepared_area.contains(rect):
                slot_polygon = rotate(rect, angle, origin=origin, use_radians=False)
                centroid = slot_polygon.centroid
                code = _slot_code(config.parking_lot_id, row_index, global_sequence)
                slots.append(
                    {
                        "slot_id": code,
                        "slot_number": code,
                        "slot_code": code,
                        "parking_lot_id": config.parking_lot_id,
                        "area_id": config.area_id,
                        "slot_type": config.slot_type,
                        "status": "available",
                        "row": row_index + 1,
                        "col": col_index + 1,
                        "row_index": row_index,
                        "col_index": col_index,
                        "x": _round_point(centroid.x),
                        "y": _round_point(centroid.y),
                        "width_m": config.slot_width_m,
                        "length_m": config.slot_length_m,
                        "width_px": _round_point(slot_width_px),
                        "height_px": _round_point(slot_length_px),
                        "angle": angle,
                        "points": _polygon_points(slot_polygon),
                    }
                )
                row_has_slot = True
                col_index += 1
                global_sequence += 1
                if len(slots) >= max_slots:
                    return {"slots": slots, "pattern": pattern, "offset_x_ratio": offset_x_ratio, "offset_y_ratio": offset_y_ratio}
            x += slot_width_px
        if row_has_slot:
            row_index += 1

    return {"slots": slots, "pattern": pattern, "offset_x_ratio": offset_x_ratio, "offset_y_ratio": offset_y_ratio}


def optimize_parking_layout(
    *,
    boundary: Sequence[Dict[str, Any]],
    obstacles: Optional[Sequence[Sequence[Dict[str, Any]]]],
    scale_factor: float,
    config: LayoutConfig,
    max_slots: int = 2000,
) -> Dict[str, Any]:
    if scale_factor <= 0:
        raise LayoutValidationError("scale_factor must be greater than 0")
    if config.slot_width_m <= 0 or config.slot_length_m <= 0:
        raise LayoutValidationError("slot_width and slot_length must be greater than 0")
    if config.aisle_width_m < 0:
        raise LayoutValidationError("aisle_width must be greater than or equal to 0")
    if config.boundary_margin_m < 0 or config.obstacle_margin_m < 0:
        raise LayoutValidationError("margins must be greater than or equal to 0")

    boundary_polygon = _build_polygon(boundary, "boundary")
    raw_obstacles = []
    warnings: List[str] = []

    for index, points in enumerate(obstacles or [], start=1):
        obstacle = _build_polygon(points, f"obstacle {index}")
        clipped = obstacle.intersection(boundary_polygon)
        if clipped.is_empty:
            warnings.append(f"obstacle {index} is outside boundary and was ignored")
            continue
        if clipped.area < obstacle.area:
            warnings.append(f"obstacle {index} was clipped to boundary")
        raw_obstacles.append(clipped)

    boundary_margin_px = config.boundary_margin_m / scale_factor
    obstacle_margin_px = config.obstacle_margin_m / scale_factor
    safe_boundary = boundary_polygon.buffer(-boundary_margin_px) if boundary_margin_px else boundary_polygon
    if safe_boundary.is_empty or safe_boundary.area <= 0:
        raise LayoutValidationError("boundary is too small after applying boundary_margin")

    obstacle_union_raw = unary_union(raw_obstacles) if raw_obstacles else None
    obstacle_union_safe = (
        unary_union([obstacle.buffer(obstacle_margin_px) for obstacle in raw_obstacles])
        if raw_obstacles and obstacle_margin_px
        else obstacle_union_raw
    )
    usable_area = safe_boundary.difference(obstacle_union_safe) if obstacle_union_safe else safe_boundary
    if usable_area.is_empty or usable_area.area <= 0:
        raise LayoutValidationError("No usable area remains after obstacles and margins")

    origin = tuple(boundary_polygon.centroid.coords[0])
    tested_angles = []
    layout_options = []
    best: Optional[Dict[str, Any]] = None

    for angle in config.angles:
        best_for_angle: Optional[Dict[str, Any]] = None
        for pattern in ("double", "single"):
            for offset_x_ratio in (0.0, 0.5):
                for offset_y_ratio in (0.0, 0.5):
                    candidate = _candidate_for_angle(
                        usable_area=usable_area,
                        angle=angle,
                        origin=origin,
                        config=config,
                        scale_factor=scale_factor,
                        offset_x_ratio=offset_x_ratio,
                        offset_y_ratio=offset_y_ratio,
                        pattern=pattern,
                        max_slots=max_slots,
                    )
                    if best_for_angle is None or len(candidate["slots"]) > len(best_for_angle["slots"]):
                        best_for_angle = candidate

        valid_slots = len(best_for_angle["slots"]) if best_for_angle else 0
        pattern = best_for_angle.get("pattern") if best_for_angle else None
        layout_options.append(
            {
                "option_id": _option_id(angle, pattern),
                "angle": angle,
                "pattern": pattern,
                "total": valid_slots,
                "offset_x_ratio": best_for_angle.get("offset_x_ratio") if best_for_angle else None,
                "offset_y_ratio": best_for_angle.get("offset_y_ratio") if best_for_angle else None,
                "generated_slots": best_for_angle["slots"] if best_for_angle else [],
            }
        )
        tested_angles.append(
            {
                "angle": angle,
                "valid_slots": valid_slots,
                "pattern": pattern,
            }
        )
        if best is None or valid_slots > len(best["slots"]):
            best = {
                **(best_for_angle or {"slots": []}),
                "angle": angle,
            }

    best_slots = best["slots"] if best else []
    layout_options = sorted(layout_options, key=lambda item: item["total"], reverse=True)
    slot_area_m2 = config.slot_width_m * config.slot_length_m
    usable_area_m2 = usable_area.area * scale_factor * scale_factor
    obstacle_area_m2 = (obstacle_union_raw.area * scale_factor * scale_factor) if obstacle_union_raw else 0.0

    return {
        "success": True,
        "total": len(best_slots),
        "usable_area_m2": round(usable_area_m2, 2),
        "boundary_area_m2": round(boundary_polygon.area * scale_factor * scale_factor, 2),
        "obstacle_area_m2": round(obstacle_area_m2, 2),
        "slot_area_m2": round(slot_area_m2, 2),
        "estimated_by_area": floor(usable_area_m2 / slot_area_m2) if slot_area_m2 > 0 else 0,
        "best_angle": best.get("angle") if best else None,
        "best_pattern": best.get("pattern") if best else None,
        "tested_angles": tested_angles,
        "layout_options": layout_options,
        "generated_slots": best_slots,
        "warnings": warnings,
        "config": {
            "slot_type": config.slot_type,
            "slot_width": config.slot_width_m,
            "slot_length": config.slot_length_m,
            "aisle_width": config.aisle_width_m,
            "boundary_margin": config.boundary_margin_m,
            "obstacle_margin": config.obstacle_margin_m,
            "scale_factor": scale_factor,
            "parking_lot_id": config.parking_lot_id,
            "area_id": config.area_id,
        },
    }
