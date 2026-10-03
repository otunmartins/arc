import numpy as np
import pytest

from kinetiq_core.geometry import angle_between, dot, normalise, wrap_angle


def test_dot() -> None:
    u = np.array([[1.0, 2.0, 3.0]])
    v = np.array([[4.0, -5.0, 6.0]])
    assert dot(u, v) == pytest.approx([12.0])


def test_normalise_gives_unit_vectors() -> None:
    out = normalise(np.array([[3.0, 0.0, 4.0], [0.0, -2.0, 0.0]]))
    assert out == pytest.approx(np.array([[0.6, 0.0, 0.8], [0.0, -1.0, 0.0]]))


def test_normalise_zero_vector_is_nan() -> None:
    assert np.isnan(normalise(np.zeros((1, 3)))).all()


@pytest.mark.parametrize(
    ("v", "expected_deg"),
    [
        ((2.0, 0.0, 0.0), 0.0),
        ((1.0, np.sqrt(3.0), 0.0), 60.0),
        ((0.0, 0.0, 5.0), 90.0),
        ((-1.0, 0.0, 0.0), 180.0),
    ],
)
def test_angle_between_known_angles(v: tuple[float, float, float], expected_deg: float) -> None:
    u = np.array([[1.0, 0.0, 0.0]])
    assert np.degrees(angle_between(u, np.array([v]))) == pytest.approx([expected_deg])


def test_angle_between_zero_or_missing_vector_is_nan() -> None:
    u = np.array([[1.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    v = np.array([[0.0, 0.0, 0.0], [np.nan, 0.0, 0.0]])
    assert np.isnan(angle_between(u, v)).all()


def test_wrap_angle() -> None:
    wrapped = wrap_angle(np.array([0.0, 1.5 * np.pi, -1.5 * np.pi, 3.0]))
    assert wrapped == pytest.approx([0.0, -0.5 * np.pi, 0.5 * np.pi, 3.0])
