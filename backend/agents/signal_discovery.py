"""
CrewAI Signal Discovery Agent.

Takes a subject name and type, uses LLM + web fetching to discover
source URLs (website, blog, careers, pricing, social media, etc.)
and returns a mapping of category_key -> user_inputs values.
"""
import json
import httpx
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool


@tool("fetch_page")
def fetch_page(url: str) -> str:
    """Fetch a web page and return its HTML content (truncated to 20KB).
    Use this to verify URLs and discover links on a company's website.
    Look for navigation menus, footer links, RSS feed tags, and social media links."""
    try:
        with httpx.Client(timeout=15, follow_redirects=True, headers={"User-Agent": "CompIntelMon/0.1"}) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text[:20000]
    except Exception as e:
        return f"Error fetching {url}: {str(e)}"


def _build_prompt(subject_name: str, subject_type: str, sources_info: list[dict]) -> str:
    """Build the discovery task prompt."""
    sources_desc = []
    for s in sources_info:
        schema = s.get("user_inputs_schema", {})
        props = schema.get("properties", {})
        required = schema.get("required", [])
        fields = []
        for key, prop in props.items():
            req = " (REQUIRED)" if key in required else ""
            fields.append(f"    - {key}: {prop.get('title', key)}{req}")
        fields_str = "\n".join(fields) if fields else "    - (no specific URL needed)"
        sources_desc.append(f"  {s['category_key']} ({s['category_name']}):\n{fields_str}")

    sources_list = "\n".join(sources_desc)

    # Build the expected JSON template
    json_keys = {}
    for s in sources_info:
        schema = s.get("user_inputs_schema", {})
        props = schema.get("properties", {})
        json_keys[s["category_key"]] = {key: "URL or value here, or null if not found" for key in props}

    json_template = json.dumps(json_keys, indent=2)

    return f"""You are researching "{subject_name}" (type: {subject_type}) to find URLs for competitive intelligence monitoring.

For each source category below, find the correct URL or identifier. Use your knowledge of this company/product/service first, then verify by fetching the main website with the fetch_page tool.

Source categories and what each needs:
{sources_list}

Instructions:
1. First, determine the main website URL for "{subject_name}"
2. Fetch the main website using fetch_page to verify it and discover links
3. From the page content, look for:
   - Navigation links: blog, pricing, careers/jobs, docs/documentation, changelog/releases
   - RSS/Atom feeds: <link rel="alternate" type="application/rss+xml"> tags
   - Social media links: Twitter/X, LinkedIn, GitHub (usually in footer or header)
   - Status page: often status.{{domain}} or statuspage links
4. For SEC/financial sources, determine if the company is publicly traded
5. Return null for any source you cannot confidently determine

IMPORTANT: Return ONLY valid JSON, no other text. Use this exact structure:
{json_template}"""


def run_discovery(
    subject_name: str,
    subject_type: str,
    sources_info: list[dict],
) -> dict[str, dict]:
    """
    Run the CrewAI discovery agent. Returns dict mapping category_key to user_inputs.
    This is a SYNCHRONOUS function (CrewAI kickoff is sync).
    """
    if not sources_info:
        return {}

    prompt = _build_prompt(subject_name, subject_type, sources_info)

    agent = Agent(
        role="Competitive Intelligence URL Researcher",
        goal=f"Find source URLs and identifiers for monitoring {subject_name}",
        backstory=(
            "You are an expert at finding company information online. "
            "You know where companies publish their blogs, pricing pages, "
            "career listings, documentation, and social media profiles. "
            "You are thorough but efficient — verify with minimal fetches."
        ),
        tools=[fetch_page],
        llm="anthropic/claude-sonnet-4-20250514",
        verbose=False,
        max_iter=5,
    )

    task = Task(
        description=prompt,
        expected_output="A JSON object mapping source category keys to their discovered user_inputs values",
        agent=agent,
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    # Parse the result — CrewAI returns a CrewOutput object
    raw_text = str(result)

    # Try to extract JSON from the response
    return _parse_discovery_result(raw_text)


def _parse_discovery_result(raw_text: str) -> dict[str, dict]:
    """Parse the agent's response into a dict of category_key -> user_inputs."""
    # Try direct JSON parse first
    try:
        data = json.loads(raw_text)
        if isinstance(data, dict):
            return _clean_result(data)
    except json.JSONDecodeError:
        pass

    # Try to find JSON in markdown code blocks
    import re
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
            if isinstance(data, dict):
                return _clean_result(data)
        except json.JSONDecodeError:
            pass

    # Try to find any JSON object in the text
    brace_start = raw_text.find("{")
    if brace_start >= 0:
        # Find the matching closing brace
        depth = 0
        for i in range(brace_start, len(raw_text)):
            if raw_text[i] == "{":
                depth += 1
            elif raw_text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(raw_text[brace_start:i + 1])
                        if isinstance(data, dict):
                            return _clean_result(data)
                    except json.JSONDecodeError:
                        pass
                    break

    return {}


def _clean_result(data: dict) -> dict[str, dict]:
    """Clean the parsed result: remove null values, ensure dict values."""
    cleaned = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            continue
        # Remove null/empty values within each source's inputs
        filtered = {k: v for k, v in value.items() if v is not None and v != "" and v != "null"}
        if filtered:
            cleaned[key] = filtered
    return cleaned
