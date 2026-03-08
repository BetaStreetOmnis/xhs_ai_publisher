import pytest

from src.core.services.chrome_login_state_service import filter_xhs_state, ordered_profile_directories
from src.core.services.chrome_profile_service import ChromeProfile, ChromeProfilesDetection


@pytest.mark.unit
def test_ordered_profile_directories_prefers_requested_then_default():
    detected = ChromeProfilesDetection(
        user_data_dir="/tmp/chrome",
        profiles=[
            ChromeProfile(directory="Profile 2", name="Work"),
            ChromeProfile(directory="Default", name="Personal"),
            ChromeProfile(directory="Profile 1", name="Side"),
        ],
        default_profile_directory="Default",
    )

    ordered = ordered_profile_directories(detected, preferred_profile_directory="Profile 1")

    assert ordered == ["Profile 1", "Default", "Profile 2"]


@pytest.mark.unit
def test_filter_xhs_state_keeps_only_xiaohongshu_entries():
    raw_state = {
        "cookies": [
            {"name": "xhs", "domain": ".xiaohongshu.com", "value": "1"},
            {"name": "other", "domain": ".example.com", "value": "2"},
        ],
        "origins": [
            {"origin": "https://creator.xiaohongshu.com", "localStorage": [{"name": "a", "value": "1"}]},
            {"origin": "https://example.com", "localStorage": [{"name": "b", "value": "2"}]},
        ],
    }

    state = filter_xhs_state(raw_state)

    assert state == {
        "cookies": [{"name": "xhs", "domain": ".xiaohongshu.com", "value": "1"}],
        "origins": [
            {"origin": "https://creator.xiaohongshu.com", "localStorage": [{"name": "a", "value": "1"}]}
        ],
    }
