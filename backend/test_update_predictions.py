import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from update_predictions import clamp, display_time, haversine_km, weather_reason
from update_predictions import (
    AvailabilitySignal,
    availability_adjustment,
    return_weight,
    upset_drag,
)


class PredictionHelpersTest(unittest.TestCase):
    def test_probability_adjustments_are_capped(self):
        self.assertEqual(0.05, clamp(-1, 0.05, 0.95))
        self.assertEqual(0.95, clamp(2, 0.05, 0.95))

    def test_interstate_distance_is_plausible(self):
        adelaide = (-34.9155, 138.5962)
        perth = (-31.9512, 115.8890)
        self.assertGreater(haversine_km(adelaide, perth), 2000)

    def test_weather_reason_only_calls_out_material_conditions(self):
        self.assertIn(
            "Rain is likely",
            weather_reason(
                {"rain_probability": 80, "wind_max": 10, "temperature_max": 18}
            ),
        )
        self.assertIsNone(
            weather_reason(
                {"rain_probability": 35, "wind_max": 20, "temperature_max": 18}
            )
        )

    def test_display_time_keeps_day_title_case(self):
        value = datetime(2026, 6, 25, 19, 0, tzinfo=ZoneInfo("Australia/Adelaide"))
        self.assertEqual("Thu 7:00 pm", display_time(value))

    def test_availability_penalises_more_injured_side(self):
        home = AvailabilitySignal(burden=1.0, mix_score=0.2)
        away = AvailabilitySignal(burden=6.0, mix_score=-0.2)
        self.assertGreater(availability_adjustment(home, away), 0)

    def test_return_weight_prioritises_long_term_absences(self):
        self.assertGreater(return_weight("Season"), return_weight("Test"))
        self.assertGreater(return_weight("4-6 weeks"), return_weight("1 week"))

    def test_upset_drag_rises_for_close_split_wet_games(self):
        risk = upset_drag(
            0.61,
            {"model_count": 26, "home_tip_count": 15},
            {"rain_probability": 70, "wind_max": 20},
            True,
        )
        self.assertGreater(risk, 0.03)


if __name__ == "__main__":
    unittest.main()
