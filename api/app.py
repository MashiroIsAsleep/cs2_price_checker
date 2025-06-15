from flask import Flask, render_template, request, jsonify
import api.checker as checker  # your module

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/check_price", methods=["POST"])
def check_price():
    try:
        skin_name = request.form.get("skin_name")
        wear = request.form.get("wear")
        float_value = request.form.get("float_value")
        paint_seed = request.form.get("paint_seed")

        print(f"[DEBUG] skin_name={skin_name}, wear={wear}, float_value={float_value}, paint_seed={paint_seed}")

        if not skin_name:
            raise ValueError("Skin name is required.")

        if not wear and not float_value:
            # New: If no wear & no float, check all wears!
            result = checker.estimate_across_wears(skin_name)
        else:
            args = {
                "item": skin_name,
                "wear": wear if wear else None,
                "float": float(float_value) if float_value else None,
                "paint_seed": int(paint_seed) if paint_seed else None,
            }
            print(f"[DEBUG] args={args}")
            result = checker.estimate_expected_price(args)

        return jsonify({
            "success": True,
            "data": result,
        })

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({
            "success": False,
            "error": str(e),
        }), 400


if __name__ == "__main__":
    app.run(debug=True)
