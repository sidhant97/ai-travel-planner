import os
import json
import logging
from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI
from rag_engine import RAGEngine
from mcp_client import MCPClient
from guardrails import Guardrails
from prompts import ROUTER_SYSTEM_PROMPT, SYNTHESIS_SYSTEM_PROMPT, build_synthesis_user_prompt

load_dotenv()
logger = logging.getLogger(__name__)

class TravelAgentOrchestrator:
    def __init__(self):
        self.rag = RAGEngine()
        self.mcp = MCPClient()

        # Groq Configuration (Primary)
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.groq_client = Groq(api_key=self.groq_key) if self.groq_key else None

        # OpenAI Configuration (Backup/Fallback)
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_client = OpenAI(api_key=self.openai_key) if self.openai_key else None

    def _call_llm_with_fallback(self, messages: list, tools: list = None, preferred_provider: str = "Auto"):
        """
        Executes chat completion with automated fallback.
        Priority: Groq -> OpenAI (if preferred_provider is 'Auto' or 'Groq')
        """
        use_openai_first = preferred_provider == "OpenAI"

        # Route to OpenAI directly if requested
        if use_openai_first and self.openai_client:
            try:
                kwargs = {"model": self.openai_model, "messages": messages, "temperature": 0.2}
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                res = self.openai_client.chat.completions.create(**kwargs)
                return res, "OpenAI (Manual)"
            except Exception as err:
                logger.error(f"OpenAI error: {err}")

        # Try Groq first (Default behavior)
        if self.groq_client:
            try:
                kwargs = {"model": self.groq_model, "messages": messages, "temperature": 0.2}
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                res = self.groq_client.chat.completions.create(**kwargs)
                return res, "Groq"
            except Exception as groq_err:
                logger.warning(f"Groq failed ({groq_err}). Triggering OpenAI backup failover...")

        # Fallback to OpenAI if Groq fails or wasn't configured
        if self.openai_client:
            try:
                kwargs = {"model": self.openai_model, "messages": messages, "temperature": 0.2}
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"
                res = self.openai_client.chat.completions.create(**kwargs)
                return res, "OpenAI (Fallback)"
            except Exception as openai_err:
                raise RuntimeError(f"Both Primary (Groq) and Fallback (OpenAI) failed. Groq error, OpenAI error: {openai_err}")

        raise RuntimeError("No operational LLM provider available. Check your API keys in .env.")

    def process_query(self, user_query: str, chat_history: list = None, preferred_provider: str = "Auto") -> dict:
        # 1. Input Guardrails
        check = Guardrails.validate_input(user_query)
        if not check["is_valid"]:
            return {
                "reply": check["reason"],
                "sources": [],
                "mcp_data": [],
                "provider_used": "Guardrails"
            }

        # 2. Tool-Routing Assessment
        tools = self.mcp.get_tool_definitions()
        router_messages = [
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_query}
        ]

        tool_call_res, routing_provider = self._call_llm_with_fallback(
            messages=router_messages,
            tools=tools,
            preferred_provider=preferred_provider
        )

        executed_mcp_data = []
        response_msg = tool_call_res.choices[0].message

        if response_msg.tool_calls:
            for call in response_msg.tool_calls:
                fn_name = call.function.name
                fn_args = json.loads(call.function.arguments)
                result = self.mcp.execute_tool(fn_name, fn_args)
                executed_mcp_data.append({"tool": fn_name, "args": fn_args, "result": result})

        # 3. Document Retrieval via RAG
        retrieved_chunks = self.rag.retrieve(user_query, top_k=3)
        knowledge_context = "\n\n".join([f"[{c['source']}]\n{c['content']}" for c in retrieved_chunks])

        # 4. Synthesize Final Response
        mcp_data_str = json.dumps(executed_mcp_data, indent=2) if executed_mcp_data else ""
        user_prompt_content = build_synthesis_user_prompt(user_query, knowledge_context, mcp_data_str)

        final_messages = [{"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT}]
        if chat_history:
            final_messages.extend(chat_history[-4:])
        final_messages.append({"role": "user", "content": user_prompt_content})

        completion, final_provider = self._call_llm_with_fallback(
            messages=final_messages,
            tools=None,
            preferred_provider=preferred_provider
        )

        reply = completion.choices[0].message.content
        sources = list(set([c["source"] for c in retrieved_chunks]))

        return {
            "reply": reply,
            "sources": sources,
            "mcp_data": executed_mcp_data,
            "provider_used": final_provider
        }