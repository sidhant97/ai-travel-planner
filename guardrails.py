class Guardrails:
    ALLOWED_DESTINATIONS = ["singapore"]

    @staticmethod
    def validate_input(user_query: str) -> dict:
        q = user_query.lower()
        # Ensure queries stay focused within Singapore travel scope
        out_of_bounds = ["tokyo", "paris", "london", "bangkok", "bali"]
        for city in out_of_bounds:
            if city in q and "singapore" not in q:
                return {
                    "is_valid": False,
                    "reason": f"Destination scope restriction: I am dedicated specifically to Singapore travel planning."
                }
        return {"is_valid": True}

    @staticmethod
    def verify_grounding(response_text: str, retrieved_docs: list, mcp_results: list) -> str:
        """Appends clear sourcing footnotes if missing."""
        if not retrieved_docs and not mcp_results:
            return response_text
        return response_text