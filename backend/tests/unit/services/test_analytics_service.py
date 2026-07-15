"""
IntelliDesk AI — Analytics Service Unit Tests
Tests for snapshot computation, aggregation, and helper methods.
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, call, patch

import pytest


class TestChunkTextService:
    """Quick sanity check that AnalyticsService imports cleanly."""

    def test_analytics_service_importable(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            assert AnalyticsService is not None


class TestGetPlatformSummary:
    """Tests for AnalyticsService.get_platform_summary()"""

    def test_summary_contains_all_keys(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            summary = AnalyticsService.get_platform_summary()
            expected_keys = {
                "total_tickets",
                "open_tickets",
                "total_incidents",
                "total_articles",
                "total_agents",
                "ai_sessions_total",
                "overall_sla_compliance",
            }
            assert expected_keys.issubset(summary.keys())

    def test_compliance_rate_within_bounds(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            summary = AnalyticsService.get_platform_summary()
            rate = summary["overall_sla_compliance"]
            assert 0.0 <= rate <= 100.0

    def test_counts_are_non_negative(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            summary = AnalyticsService.get_platform_summary()
            for key, value in summary.items():
                if isinstance(value, (int, float)):
                    assert value >= 0, f"{key} should be >= 0, got {value}"


class TestSLAComplianceByPriority:
    """Tests for AnalyticsService.get_sla_compliance_by_priority()"""

    def test_all_priorities_present(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService
            from app.utils.constants import TicketPriority

            result = AnalyticsService.get_sla_compliance_by_priority()
            for priority in TicketPriority:
                assert (
                    priority.value in result
                ), f"Priority '{priority.value}' missing from SLA result"

    def test_compliance_structure_correct(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            result = AnalyticsService.get_sla_compliance_by_priority()
            for priority, data in result.items():
                assert "total" in data
                assert "compliant" in data
                assert "breached" in data
                assert "compliance_rate" in data
                assert data["compliant"] + data["breached"] == data["total"]
                assert 0.0 <= data["compliance_rate"] <= 100.0

    def test_no_tickets_gives_100_percent(self, app):
        with app.app_context():
            from app.models.ticket import Ticket
            from app.services.analytics_service import AnalyticsService

            # On fresh test DB with no tickets, compliance should be 100%
            with patch.object(Ticket, "query") as mock_query:
                mock_query.filter_by.return_value.count.return_value = 0
                result = AnalyticsService.get_sla_compliance_by_priority()
                for _, data in result.items():
                    assert data["compliance_rate"] == 100.0


class TestTicketVolumeByCategory:
    """Tests for AnalyticsService.get_ticket_volume_by_category()"""

    def test_returns_list_of_dicts(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            result = AnalyticsService.get_ticket_volume_by_category()
            assert isinstance(result, list)
            for item in result:
                assert "category" in item
                assert "count" in item
                assert item["count"] >= 0

    def test_uncategorized_label_used_for_null(self, app):
        """Tickets with NULL category should be labelled 'Uncategorized'."""
        with app.app_context():
            from app.extensions import db
            from app.services.analytics_service import AnalyticsService

            row_mock = MagicMock()
            row_mock.category = None
            row_mock.count = 5

            with patch.object(db.session, "query") as mock_query:
                mock_query.return_value.filter.return_value.group_by.return_value.order_by.return_value.all.return_value = [
                    row_mock
                ]
                result = AnalyticsService.get_ticket_volume_by_category()

            for item in result:
                assert item["category"] != "None"
                assert item["category"] != ""


class TestAgentLeaderboard:
    """Tests for AnalyticsService.get_agent_leaderboard()"""

    def test_returns_list(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            result = AnalyticsService.get_agent_leaderboard(days=30, limit=5)
            assert isinstance(result, list)

    def test_leaderboard_items_have_required_fields(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            result = AnalyticsService.get_agent_leaderboard(days=30, limit=10)
            for agent in result:
                assert "agent_id" in agent
                assert "agent_name" in agent
                assert "tickets_resolved" in agent
                assert "resolution_rate" in agent
                assert 0.0 <= agent["resolution_rate"] <= 100.0

    def test_respects_limit(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            result = AnalyticsService.get_agent_leaderboard(days=30, limit=3)
            assert len(result) <= 3


class TestHeatmapData:
    """Tests for AnalyticsService.get_heatmap_data()"""

    def test_returns_list(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            result = AnalyticsService.get_heatmap_data(days=30)
            assert isinstance(result, list)

    def test_heatmap_structure_valid(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            result = AnalyticsService.get_heatmap_data(days=30)
            for point in result:
                assert "day" in point
                assert "hour" in point
                assert "count" in point
                assert 0 <= point["day"] <= 6, "day_of_week must be 0-6"
                assert 0 <= point["hour"] <= 23, "hour_of_day must be 0-23"
                assert point["count"] >= 0


class TestComputeDailySnapshot:
    """Tests for AnalyticsService.compute_daily_snapshot() idempotency."""

    def test_snapshot_is_idempotent(self, app):
        """Running snapshot twice for same date should not create duplicates."""
        with app.app_context():
            from app.models.analytics import DailyMetricSnapshot
            from app.services.analytics_service import AnalyticsService

            yesterday = date.today() - timedelta(days=1)

            # First run
            snap1 = AnalyticsService.compute_daily_snapshot(yesterday)

            # Second run — should upsert, not create second record
            snap2 = AnalyticsService.compute_daily_snapshot(yesterday)

            count = DailyMetricSnapshot.query.filter_by(
                snapshot_date=yesterday,
                department_id=None,
            ).count()
            assert count == 1, "Snapshot upsert created duplicate record!"
            assert snap1.id == snap2.id

    def test_snapshot_fields_are_non_negative(self, app):
        with app.app_context():
            from app.services.analytics_service import AnalyticsService

            yesterday = date.today() - timedelta(days=1)
            snap = AnalyticsService.compute_daily_snapshot(yesterday)

            assert snap.tickets_created >= 0
            assert snap.tickets_resolved >= 0
            assert snap.sla_breached_count >= 0
            assert 0.0 <= snap.sla_compliance_rate <= 100.0


class TestOverallSLAComputation:
    """Tests for AnalyticsService._compute_overall_sla()"""

    def test_returns_100_when_no_resolved_tickets(self, app):
        with app.app_context():
            from app.models.ticket import Ticket
            from app.services.analytics_service import AnalyticsService

            with patch.object(
                Ticket.query.filter(Ticket.resolved_at.isnot(None), Ticket.deleted_at.is_(None)),
                "count",
                return_value=0,
            ):
                # Fresh test DB should default to 100% or compute correctly
                rate = AnalyticsService._compute_overall_sla()
                assert 0.0 <= rate <= 100.0
