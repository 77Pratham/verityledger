"""
Example: a tiny "agent" that looks up weather and decides whether to
recommend an umbrella, fully traced by VerityLedger.

Run: python examples/basic_demo.py
"""

from verityledger import Tracer

tracer = Tracer(log_path="./demo_log.jsonl")

with tracer.session(agent="weather-assistant", user="demo-user") as session:

    @session.trace_tool
    def get_weather(city: str) -> dict:
        return {"city": city, "forecast": "sunny", "temp_c": 29}

    @session.trace_tool
    def divide(a: int, b: int) -> float:
        return a / b

    weather = get_weather("Mumbai")

    session.log_model_call(
        prompt="Should I bring an umbrella in Mumbai today?",
        response="No, it's sunny — no umbrella needed.",
        model="claude-sonnet-4-6",
    )

    session.log_decision(
        decision="recommend no umbrella",
        reasoning="forecast is sunny with no rain probability",
        forecast=weather,
    )

    try:
        divide(10, 0)
    except ZeroDivisionError:
        session.log_decision(
            decision="fallback to default response",
            reasoning="division tool failed, used cached estimate instead",
        )

    print(f"Session id: {session.id}")

valid, break_index = tracer.verify(session.id)
print(f"Chain valid: {valid} (break at: {break_index})")

report = tracer.export_report(session.id, "report.json")
print(f"Exported {report['entry_count']} entries to report.json")
