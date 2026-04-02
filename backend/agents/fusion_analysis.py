"""
CrewAI Fusion Analysis Agent.

Reads collected data from multiple sources for a subject and extracts
structured competitive intelligence: summary, key findings, and signals.
"""
import json
import re
from crewai import Agent, Task, Crew, Process


def _build_analysis_prompt(subject_name: str, subject_type: str, sources_data: list[dict]) -> str:
    """Build the analysis task prompt with collected data."""
    sources_section = []
    for s in sources_data:
        content = s.get("raw_content", "")[:15000]  # cap per source
        instructions = s.get("signal_instructions", "")
        sources_section.append(
            f"### Source: {s['category_name']} ({s['category_key']})\n"
            f"**Analysis guidance:** {instructions}\n\n"
            f"**Collected content:**\n{content}\n"
        )

    all_sources = "\n---\n".join(sources_section)

    return f"""You are analyzing "{subject_name}" (type: {subject_type}) for competitive intelligence.

Below is collected data from {len(sources_data)} sources. Analyze this data and extract:

1. **Summary**: A 2-3 paragraph executive summary of the competitive intelligence picture
2. **Key Findings**: Specific, actionable findings (max 10)
3. **Signals**: Competitive signals that indicate strategic direction, changes, or opportunities

For each key finding, include:
- category: which source category it came from
- finding: the specific finding
- severity: "high", "medium", or "low"
- source_key: the category_key of the source

For each signal, include:
- signal_type: e.g., "hiring_pattern", "pricing_change", "product_launch", "market_expansion", "partnership", "technology_shift"
- description: what the signal indicates
- confidence: "high", "medium", or "low"
- source_key: the category_key of the source

Return ONLY valid JSON in this exact format:
{{
  "summary": "Executive summary text here...",
  "key_findings": [
    {{"category": "...", "finding": "...", "severity": "high|medium|low", "source_key": "..."}}
  ],
  "signals": [
    {{"signal_type": "...", "description": "...", "confidence": "high|medium|low", "source_key": "..."}}
  ]
}}

--- COLLECTED DATA ---

{all_sources}"""


def run_fusion_analysis(
    subject_name: str,
    subject_type: str,
    sources_data: list[dict],
) -> dict:
    """
    Run the Fusion analysis agent. Returns dict with summary, key_findings, signals.
    SYNCHRONOUS function (CrewAI kickoff is sync).
    """
    if not sources_data:
        return {"summary": "No data available for analysis.", "key_findings": [], "signals": []}

    prompt = _build_analysis_prompt(subject_name, subject_type, sources_data)

    agent = Agent(
        role="Competitive Intelligence Analyst",
        goal=f"Analyze collected data about {subject_name} and extract actionable competitive intelligence",
        backstory=(
            "You are a senior competitive intelligence analyst with 15 years of experience. "
            "You excel at identifying strategic signals from diverse data sources — website changes, "
            "job postings, news articles, social media, and financial data. You focus on actionable "
            "insights, not just summaries."
        ),
        llm="anthropic/claude-sonnet-4-20250514",
        verbose=False,
        max_iter=3,
    )

    task = Task(
        description=prompt,
        expected_output="JSON object with summary, key_findings array, and signals array",
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()
    return _parse_analysis_result(str(result))


def _parse_analysis_result(raw_text: str) -> dict:
    """Parse the agent's response into structured analysis."""
    default = {"summary": "", "key_findings": [], "signals": []}

    # Try direct JSON parse
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict) and "summary" in data:
            return data
    except json.JSONDecodeError:
        pass

    # Try markdown code blocks
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if isinstance(data, dict) and "summary" in data:
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
                        if isinstance(data, dict) and "summary" in data:
                            return data
                    except json.JSONDecodeError:
                        pass
                    break

    # Fallback: treat entire text as summary
    return {**default, "summary": raw_text[:2000]}
