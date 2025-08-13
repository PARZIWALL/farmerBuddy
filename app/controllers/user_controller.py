from flask import Blueprint, jsonify, request

from ..services.user_service import create_user, get_user_by_id, list_users


user_bp = Blueprint("users", __name__)


@user_bp.get("/")
def get_users():
    users = list_users()
    return jsonify(users), 200


@user_bp.get("/<int:user_id>")
def get_user(user_id: int):
    user = get_user_by_id(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user), 200


@user_bp.post("/")
def post_user():
    payload = request.get_json(silent=True) or {}
    name = payload.get("name")
    if not name:
        return jsonify({"error": "name is required"}), 400
    user = create_user(name)
    return jsonify(user), 201


