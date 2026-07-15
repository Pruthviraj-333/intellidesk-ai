"""
IntelliDesk AI — Analytics Controller (Blueprint)
HTTP handlers for KPI metrics, trends, heatmaps, and leaderboards.
Route prefix: /api/v1/analytics
"""

from flask import Blueprint

from app.dtos.analytics_dto import (
    AgentLeaderboardItemSchema,
    DailyTrendPointSchema,
    HeatmapPointSchema,
    HeatmapQuerySchema,
    LeaderboardQuerySchema,
    PlatformSummarySchema,
    TicketVolumeItemSchema,
    TrendQuerySchema,
)
from app.services.analytics_service import AnalyticsService
from app.utils.constants import UserRole
from app.utils.decorators import jwt_required_any, role_required, validate_query
from app.utils.response import success_response

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/v1/analytics")


@analytics_bp.route("/summary", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_platform_summary():
    """
    GET /api/v1/analytics/summary
    High-level platform KPIs: total tickets, open, SLA compliance, agents, AI usage.
    Access: Manager+
    """
    summary = AnalyticsService.get_platform_summary()
    return success_response(PlatformSummarySchema().dump(summary))


@analytics_bp.route("/trends", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_query(TrendQuerySchema)
def get_trends(params: dict):
    """
    GET /api/v1/analytics/trends?days=30
    Daily ticket, incident, and AI metrics from pre-aggregated snapshots.
    Used to power the time-series line chart on the analytics dashboard.
    """
    trends = AnalyticsService.get_trend_data(
        days=params["days"],
        department_id=params.get("department_id"),
    )
    return success_response(
        {
            "period_days": params["days"],
            "data_points": len(trends),
            "trends": DailyTrendPointSchema(many=True).dump(trends),
        }
    )


@analytics_bp.route("/sla-compliance", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_sla_compliance():
    """
    GET /api/v1/analytics/sla-compliance
    Live SLA compliance rates broken down by ticket priority.
    Used to power the SLA compliance bar/donut chart.
    """
    sla = AnalyticsService.get_sla_compliance_by_priority()
    return success_response({"sla_by_priority": sla})


@analytics_bp.route("/ticket-volume", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
def get_ticket_volume():
    """
    GET /api/v1/analytics/ticket-volume
    Ticket count breakdown by category for the pie/bar chart.
    """
    volume = AnalyticsService.get_ticket_volume_by_category()
    return success_response(TicketVolumeItemSchema(many=True).dump(volume))


@analytics_bp.route("/agent-leaderboard", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_query(LeaderboardQuerySchema)
def get_agent_leaderboard(params: dict):
    """
    GET /api/v1/analytics/agent-leaderboard?days=30&limit=10
    Top agents by resolution count over the specified period.
    Used for performance tracking and team reports.
    """
    leaderboard = AnalyticsService.get_agent_leaderboard(
        days=params["days"],
        limit=params["limit"],
    )
    return success_response(
        {
            "period_days": params["days"],
            "agents": AgentLeaderboardItemSchema(many=True).dump(leaderboard),
        }
    )


@analytics_bp.route("/heatmap", methods=["GET"])
@role_required(UserRole.MANAGER, UserRole.ADMIN, UserRole.SUPER_ADMIN)
@validate_query(HeatmapQuerySchema)
def get_heatmap(params: dict):
    """
    GET /api/v1/analytics/heatmap?days=90
    Ticket creation counts by hour-of-day × day-of-week.
    Used to render the calendar heatmap showing peak support hours.
    """
    heatmap = AnalyticsService.get_heatmap_data(days=params["days"])
    return success_response(
        {
            "period_days": params["days"],
            "heatmap": HeatmapPointSchema(many=True).dump(heatmap),
        }
    )
