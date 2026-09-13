import streamlit as st
import datetime
import json
from orchestrator import TravelAgentOrchestrator

st.set_page_config(page_title="AI Travel Assistant", page_icon="✈️", layout="wide")

st.title("Travel Assistant")
st.caption("Primary: Groq  | Fallback: OpenAI | ChromaDB RAG | MCP Live Tools")

@st.cache_resource
def get_orchestrator():
    return TravelAgentOrchestrator()

orchestrator = get_orchestrator()

def format_chat_for_download(messages):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    doc = "============================================================\n"
    doc += "TRAVEL ASSISTANT - ITINERARY & SESSION EXPORT\n"
    doc += f"Exported: {timestamp}\n"
    doc += "============================================================\n\n"
    
    for idx, msg in enumerate(messages, 1):
        role_tag = "USER QUERY" if msg["role"] == "user" else "ASSISTANT PLAN & RESPONSE"
        doc += f"[{idx}] {role_tag}:\n"
        doc += f"{msg['content']}\n\n"
        
        meta = msg.get("metadata", {})
        if meta.get("provider"):
            doc += f"-- MODEL ENGINE USED: {meta['provider']} --\n"
        if meta.get("mcp_data"):
            doc += "-- MCP LIVE TOOL EXECUTION DETAILS --\n"
            doc += json.dumps(meta["mcp_data"], indent=2) + "\n\n"
        if meta.get("sources"):
            doc += f"-- RAG GROUNDED SOURCES --\n{', '.join(meta['sources'])}\n\n"
        
        doc += "-" * 60 + "\n\n"
    return doc

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar Destination Selection & Controls
with st.sidebar:
    st.header("Destination Options")
    selected_country = st.selectbox(
        "Select Country / Destination:",
        options=["Singapore", "Japan (Coming Soon)", "France (Coming Soon)", "Thailand (Coming Soon)"],
        index=0,
        help="Currently, knowledge base and MCP tool pipelines are configured strictly for Singapore."
    )

    is_supported = selected_country == "Singapore"
    
    if not is_supported:
        st.warning("Scope Constraint: Only Singapore is currently supported by the RAG corpus and real-time MCP tool integrations.")

    st.header("Model Engine Provider")
    provider_choice = st.selectbox(
        "LLM Provider Strategy:",
        options=["Auto (Groq Default + OpenAI Backup)", "Groq Only", "OpenAI"],
        index=0,
        help="Defaults to free Groq tier; falls back seamlessly to OpenAI if rate limits or network issues arise."
    )
    provider_mode = "Auto" if "Auto" in provider_choice else ("OpenAI" if "OpenAI" in provider_choice else "Groq")

    st.divider()
    st.header("Quick Test Scenarios")
    st.markdown("**1. RAG Only:**")
    if st.button("Must-visit attractions in Singapore", disabled=not is_supported):
        st.session_state.preset_query = "What are the must-visit attractions in Singapore?"

    st.markdown("**2. MCP Tools Only:**")
    if st.button("Convert INR 60,000 to SGD", disabled=not is_supported):
        st.session_state.preset_query = "Convert INR 60,000 to SGD"
    if st.button("Check 3-day weather", disabled=not is_supported):
        st.session_state.preset_query = "What is the weather forecast for the next three days in Singapore?"

    st.markdown("**3. Combined RAG + MCP:**")
    if st.button("3-Day Weather-Aware Itinerary", disabled=not is_supported):
        st.session_state.preset_query = "Create a 3-day Singapore itinerary for next week and adjust it according to the weather forecast with indoor options."
    if st.button("Budget + Itinerary", disabled=not is_supported):
        st.session_state.preset_query = "I have a budget of INR 60,000. Convert it to SGD and suggest a three-day itinerary."

    st.divider()
    if st.session_state.messages:
        full_transcript = format_chat_for_download(st.session_state.messages)
        st.download_button(
            label="📄 Download Entire Session (.txt)",
            data=full_transcript,
            file_name=f"singapore_travel_session_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True
        )

# Main chat flow
for idx, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "metadata" in msg:
            meta = msg["metadata"]
            if meta.get("provider"):
                st.caption(f"Engine: `{meta['provider']}`")
            if meta.get("mcp_data"):
                with st.expander("🛠️ MCP Tool Execution Details"):
                    st.json(meta["mcp_data"])
            if meta.get("sources"):
                st.caption(f"Grounded Sources: {', '.join(meta['sources'])}")

            if msg["role"] == "assistant":
                single_export = f"=== SINGAPORE TRIP PLAN ===\nGenerated: {datetime.datetime.now()}\n"
                single_export += f"Engine: {meta.get('provider', 'N/A')}\n\n"
                single_export += f"{msg['content']}\n\n"
                if meta.get("sources"):
                    single_export += f"Sources: {', '.join(meta['sources'])}\n"
                if meta.get("mcp_data"):
                    single_export += f"MCP Tools: {json.dumps(meta['mcp_data'], indent=2)}\n"

                st.download_button(
                    label="Download Plan (.txt)",
                    data=single_export,
                    file_name=f"singapore_itinerary_{idx}.txt",
                    mime="text/plain",
                    key=f"dl_{idx}"
                )

if not is_supported:
    st.info("Please switch the destination dropdown back to **Singapore** to interact with the planner.")
    user_query = None
else:
    user_query = st.chat_input("Ask a question about Singapore travel...")

if "preset_query" in st.session_state and st.session_state.preset_query:
    user_query = st.session_state.preset_query
    st.session_state.preset_query = None

if user_query and is_supported:
    st.chat_message("user").markdown(user_query)
    history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
    
    with st.spinner("Processing RAG embeddings and MCP live feeds..."):
        res = orchestrator.process_query(user_query, history, preferred_provider=provider_mode)

    with st.chat_message("assistant"):
        st.markdown(res["reply"])
        st.caption(f"⚡ Engine: `{res['provider_used']}`")
        if res["mcp_data"]:
            with st.expander("🛠️ MCP Tool Execution Details"):
                st.json(res["mcp_data"])
        if res["sources"]:
            st.caption(f"📚 Grounded Sources: {', '.join(res['sources'])}")

        single_export = f"=== SINGAPORE TRIP PLAN ===\nEngine: {res['provider_used']}\n\n{res['reply']}\n\n"
        if res["sources"]:
            single_export += f"Sources: {', '.join(res['sources'])}\n"
        if res["mcp_data"]:
            single_export += f"MCP Tools: {json.dumps(res['mcp_data'], indent=2)}\n"

        st.download_button(
            label="💾 Download Plan (.txt)",
            data=single_export,
            file_name=f"singapore_itinerary_{len(st.session_state.messages)+1}.txt",
            mime="text/plain",
            key=f"dl_latest_{len(st.session_state.messages)}"
        )

    st.session_state.messages.append({"role": "user", "content": user_query})
    st.session_state.messages.append({
        "role": "assistant",
        "content": res["reply"],
        "metadata": {
            "sources": res["sources"],
            "mcp_data": res["mcp_data"],
            "provider": res["provider_used"]
        }
    })