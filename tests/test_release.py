"""Tests for Release Manager."""
from core.release import ReleaseManager, ReleaseStatus, VersionBump


class TestReleaseManager:
    def test_create(self):
        rm = ReleaseManager()
        assert rm.current_version == "0.1.0"
        assert rm._releases == {}

    def test_create_with_version(self):
        rm = ReleaseManager("1.2.3")
        assert rm.current_version == "1.2.3"

    def test_bump_patch(self):
        rm = ReleaseManager("1.2.3")
        version = rm.bump_version(VersionBump.PATCH)
        assert version == "1.2.4"

    def test_bump_minor(self):
        rm = ReleaseManager("1.2.3")
        version = rm.bump_version(VersionBump.MINOR)
        assert version == "1.3.0"

    def test_bump_major(self):
        rm = ReleaseManager("1.2.3")
        version = rm.bump_version(VersionBump.MAJOR)
        assert version == "2.0.0"

    def test_create_release(self):
        rm = ReleaseManager()
        release = rm.create_release()
        assert release.status == ReleaseStatus.DRAFT
        assert release.version == "0.1.0"
        assert release.id in rm._releases

    def test_create_release_with_version(self):
        rm = ReleaseManager()
        release = rm.create_release(version="2.0.0")
        assert release.version == "2.0.0"

    def test_add_change(self):
        rm = ReleaseManager()
        entry = rm.add_change("1.0.0", "Fixed bug", "fixed")
        assert entry.version == "1.0.0"
        assert entry.description == "Fixed bug"

    def test_publish_release(self):
        rm = ReleaseManager()
        release = rm.create_release()
        assert rm.publish_release(release.id) is True
        assert rm.get_release(release.id).status == ReleaseStatus.PUBLISHED

    def test_publish_release_missing(self):
        rm = ReleaseManager()
        assert rm.publish_release("nonexistent") is False

    def test_get_release(self):
        rm = ReleaseManager()
        release = rm.create_release()
        result = rm.get_release(release.id)
        assert result is not None
        assert result.id == release.id

    def test_list_releases(self):
        rm = ReleaseManager()
        rm.create_release()
        rm.create_release()
        assert len(rm.list_releases()) == 2

    def test_get_changelog(self):
        rm = ReleaseManager()
        rm.add_change("1.0.0", "Feature A")
        rm.add_change("1.0.0", "Feature B")
        rm.add_change("2.0.0", "Feature C")
        entries = rm.get_changelog("1.0.0")
        assert len(entries) == 2

    def test_get_latest_release(self):
        rm = ReleaseManager()
        r1 = rm.create_release("1.0.0")
        r2 = rm.create_release("2.0.0")
        rm.publish_release(r1.id)
        rm.publish_release(r2.id)
        latest = rm.get_latest_release()
        assert latest is not None

    def test_get_state(self):
        rm = ReleaseManager()
        rm.create_release()
        state = rm.get_state()
        assert state["current_version"] == "0.1.0"
        assert state["total_releases"] == 1
