def success_response(message, data=None):
    return {"success": True, "message": message, "data": data or {}}


def error_response(message, errors=None):
    return {"success": False, "message": message, "errors": errors or {}}
