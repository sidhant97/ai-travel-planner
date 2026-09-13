from orchestrator import TravelAgentOrchestrator

def run_tests():
    agent = TravelAgentOrchestrator()
    print("--- 1. Testing RAG Destination Knowledge ---")
    r1 = agent.process_query("What are cultural neighborhoods to visit in Singapore?")
    assert len(r1["sources"]) > 0
    print("✅ RAG Verified. Sources:", r1["sources"])

    print("\n--- 2. Testing MCP Currency Tool ---")
    r2 = agent.process_query("Convert INR 50,000 to SGD")
    assert any(m["tool"] == "convert_currency" for m in r2["mcp_data"])
    print("✅ Currency Tool Verified. Result:", r2["mcp_data"])

    print("\n--- 3. Testing Combined RAG + Weather MCP ---")
    r3 = agent.process_query("Plan a 3-day itinerary adjusted for weather")
    assert any(m["tool"] == "get_weather" for m in r3["mcp_data"])
    print("✅ Combined Scenario Verified.")

if __name__ == "__main__":
    run_tests()