import os
import json
import logging
from dotenv import load_dotenv

# Ensure environment variables load before LangChain components initialize
load_dotenv()

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import StructuredTool
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI

from rag_engine import RAGEngine
from mcp_client import MCPClient
from guardrails import Guardrails
from prompts import ROUTER_SYSTEM_PROMPT, SYNTHESIS_SYSTEM_PROMPT, build_synthesis_user_prompt

logger = logging.getLogger(__name__)


class TravelAgentOrchestrator:
    def __init__(self):
        self.rag = RAGEngine()
        self.mcp = MCPClient()

        # Groq Configuration (Primary)
        self.groq_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
        self.groq_llm = (
            ChatGroq(
                model=self.groq_model,
                groq_api_key=self.groq_key,
                temperature=0.2,
            )
            if self.groq_key
            else None
        )

        # OpenAI Configuration (Backup/Fallback)
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_llm = (
            ChatOpenAI(
                model=self.openai_model,
                api_key=self.openai_key,
                temperature=0.2,
            )
            if self.openai_key
            else None
        )

    def _convert_messages_to_langchain(self, raw_messages: list) -> list:
        """Converts raw dict messages to LangChain BaseMessage instances."""
        formatted = []
        for msg in raw_messages:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "system":
                formatted.append(SystemMessage(content=content))
            elif role == "assistant":
                formatted.append(AIMessage(content=content))
            else:
                formatted.append(HumanMessage(content=content))
        return formatted

    def _get_active_chain(self, preferred_provider: str = "Auto", tools: list = None):
        """
        Builds the invocation chain using LangChain's native .with_fallbacks().
        Automatically logs model runs, token counts, and fallbacks to LangSmith.
        """
        groq_model = self.groq_llm
        openai_model = self.openai_llm

        if tools:
            if groq_model:
                groq_model = groq_model.bind_tools(tools)
            if openai_model:
                openai_model = openai_model.bind_tools(tools)

        use_openai_first = preferred_provider == "OpenAI"

        if use_openai_first and openai_model:
            return openai_model.with_fallbacks([groq_model]) if groq_model else openai_model
        
        if groq_model:
            return groq_model.with_fallbacks([openai_model]) if openai_model else groq_model

        if openai_model:
            return openai_model

        raise RuntimeError("No operational LLM provider available. Check your API keys in .env.")

    def process_query(self, user_query: str, chat_history: list = None, preferred_provider: str = "Auto") -> dict:
        # 1. Input Guardrails
        check = Guardrails.validate_input(user_query)
        if not check["is_valid"]:
            return {
                "reply": check["reason"],
                "sources": [],
                "mcp_data": [],
                "provider_used": "Guardrails",
            }

        # 2. Tool-Routing Assessment
        raw_tools = self.mcp.get_tool_definitions()
        router_messages = self._convert_messages_to_langchain([
            {"role": "system", "content": ROUTER_SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ])

        router_chain = self._get_active_chain(preferred_provider=preferred_provider, tools=raw_tools)
        tool_call_res = router_chain.invoke(router_messages)

        executed_mcp_data = []
        if hasattr(tool_call_res, "tool_calls") and tool_call_res.tool_calls:
            for call in tool_call_res.tool_calls:
                fn_name = call["name"]
                fn_args = call["args"]
                result = self.mcp.execute_tool(fn_name, fn_args)
                executed_mcp_data.append({"tool": fn_name, "args": fn_args, "result": result})

        # 3. Document Retrieval via RAG
        retrieved_chunks = self.rag.retrieve(user_query, top_k=3)
        knowledge_context = "\n\n".join([f"[{c['source']}]\n{c['content']}" for c in retrieved_chunks])

        # 4. Synthesize Final Response
        mcp_data_str = json.dumps(executed_mcp_data, indent=2) if executed_mcp_data else ""
        user_prompt_content = build_synthesis_user_prompt(user_query, knowledge_context, mcp_data_str)

        raw_final_messages = [{"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT}]
        if chat_history:
            raw_final_messages.extend(chat_history[-4:])
        raw_final_messages.append({"role": "user", "content": user_prompt_content})

        final_messages = self._convert_messages_to_langchain(raw_final_messages)
        synthesis_chain = self._get_active_chain(preferred_provider=preferred_provider, tools=None)
        completion = synthesis_chain.invoke(final_messages)

        reply = completion.content
        sources = list(set([c["source"] for c in retrieved_chunks]))

        # Extract provider/model details recorded by LangChain
        provider_used = completion.response_metadata.get("model_name", preferred_provider)

        return {
            "reply": reply,
            "sources": sources,
            "mcp_data": executed_mcp_data,
            "provider_used": provider_used,
        }