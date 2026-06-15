from flask import Blueprint, jsonify, request
from ..utils.user_utils import get_user_uuid
from ..services.performance_service import get_performance_summary, get_performance_history

performance_bp = Blueprint("performance", __name__)


@performance_bp.route("/performance", methods=['GET'])
def performance():
    user_id = get_user_uuid()

    data = get_performance_summary(user_id)

    if request.args.get("history", "false").lower() in ("1", "true", "yes"):
        start_date = request.args.get("start")
        end_date = request.args.get("end")
        # Optional `days` parameter (clamped 30..1095)
        days = request.args.get("days")
        try:
            days = int(days) if days is not None else None
            if days is not None:
                days = max(30, min(days, 1095))
        except Exception:
            days = None

        data["history"] = get_performance_history(user_id, start_date=start_date, end_date=end_date, days=days or 365)

    return jsonify(data)