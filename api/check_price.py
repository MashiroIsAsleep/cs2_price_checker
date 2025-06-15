# api/check_price.py

import json
import checker  # this imports api/checker.py automatically

def handler(request):
    try:
        body = request.get_json()
        skin_name = body.get("skin_name")
        wear = body.get("wear")
        float_value = body.get("float_value")
        paint_seed = body.get("paint_seed")

        if not skin_name:
            raise ValueError("Skin name is required.")

        if not wear and not float_value:
            result = checker.estimate_across_wears(skin_name)
        else:
            args = {
                "item": skin_name,
                "wear": wear if wear else None,
                "float": float(float_value) if float_value else None,
                "paint_seed": int(paint_seed) if paint_seed else None,
            }
            result = checker.estimate_expected_price(args)

        return {
            "statusCode": 200,
            "body": json.dumps({"success": True, "data": result})
        }

    except Exception as e:
        return {
            "statusCode": 400,
            "body": json.dumps({"success": False, "error": str(e)})
        }
