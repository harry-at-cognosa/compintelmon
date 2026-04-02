"""
CrewAI Ad-hoc Update Agent.

Processes user-provided information or investigation requests.
Saves results as data files that feed into future Fusion analyses.
"""
import json
import re
from crewai import Agent, Task, Crew, Process
from backend.agents.signal_discovery import fetch_page


def run_adhoc_update(
    subject_name: str,
    subject_type: str,
    user_message: str,
    existing_data_summary: str,
) -> dict:
    """
    Process an ad-hoc update message. SYNCHRONOUS.

    Returns dict with:
    - response_text: str (what to show the user)
    - saved_data: dict | None (structured data to save)
    - message_type: "data_saved" | "collection_triggered" | "text"
    """
    prompt = f"""You are a competitive intelligence data analyst working on "{subject_name}" ({subject_type}).

The user has provided new information or a request to investigate something. Process their message and respond.

**Existing data for this subject:**
{existing_data_summary or "No data collected yet."}

**User message:**
{user_message}

**Instructions:**
1. If the user is providing DIRECT INFORMATION (e.g., "their main competitor is X", "they just raised $50M"):
   - Acknowledge and confirm what you understood
   - Return the information as structured data for saving

2. If the user provides a URL to check:
   - Use the fetch_page tool to retrieve the content
   - Summarize what you found
   - Return the key findings as structured data

3. If the user asks you to investigate something:
   - Use the fetch_page tool if needed
   - Research and return your findings

Return ONLY valid JSON in this format:
{{
  "response_text": "Your response to the user explaining what was processed/found",
  "saved_data": {{
    "source": "user_provided | url_fetched | investigation",
    "category": "competitor_info | market_data | product_info | financial_info | general",
    "summary": "Brief summary of the data",
    "details": "Full details of the information"
  }},
  "message_type": "data_saved"
}}

If no data should be saved (e.g., you need clarification), set saved_data to null and message_type to "text".
"""

    agent = Agent(
        role="Competitive Intelligence Data Analyst",
        goal=f"Process and save competitive intelligence updates about {subject_name}",
        backstory=(
            "You are a meticulous data analyst who processes incoming intelligence about "
            "companies, products, and markets. You verify information when possible, "
            "structure it for future analysis, and clearly communicate what was saved."
        ),
        tools=[fetch_page],
        llm="anthropic/claude-sonnet-4-20250514",
        verbose=False,
        max_iter=5,
    )

    task = Task(
        description=prompt,
        expected_output="JSON with response_text, saved_data, and message_type",
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()
    return _parse_update_result(str(result))


def _parse_update_result(raw_text: str) -> dict:
    """Parse the agent's response."""
    default = {"response_text": raw_text[:2000], "saved_data": None, "message_type": "text"}

    # Try direct JSON
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict) and "response_text" in data:
            return data
    except json.JSONDecodeError:
        pass

    # Try markdown code blocks
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if isinstance(data, dict) and "response_text" in data:
                return data
        except json.JSONDecodeError:
            pass

    # Try finding JSON object
    brace_start = raw_text.find("{")
    if brace_start >= 0:
        depth = 0
        for i in range(brace_start, len(raw_text)):
            if raw_text[i] == "{":
                depth += 1
            elif raw_text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(raw_text[brace_start:i + 1])
                        if isinstance(data, dict) and "response_text" in data:
                            return data
                    except json.JSONDecodeError:
                        pass
                    break

    return default
