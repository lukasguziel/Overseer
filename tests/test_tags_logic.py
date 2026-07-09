import math

from sceneorg.core.tags_logic import deg_from_rad, dominant_angle


def test_deg_from_rad_rounds_to_tenth():
    # do it
    result = deg_from_rad(math.radians(40.0))

    # postcondition
    assert result == 40.0


def test_dominant_angle_picks_most_common():
    # setup
    counts = {40.0: 3, 60.0: 1, 80.0: 3}

    # do it: ties break on the larger angle
    result = dominant_angle(counts)

    # postcondition
    assert result == 80.0


def test_dominant_angle_empty_is_none():
    # do it / postcondition
    assert dominant_angle({}) is None
