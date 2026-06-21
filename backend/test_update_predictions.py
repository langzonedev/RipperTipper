import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from update_predictions import clamp, display_time, haversine_km, weather_reason


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


if __name__ == "__main__":
    unittest.main()
