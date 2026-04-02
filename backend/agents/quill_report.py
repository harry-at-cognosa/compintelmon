"""
CrewAI Quill Report Agent.

Takes a Fusion analysis and generates a formatted competitive intelligence
report (battlecard, summary, or executive brief) in Markdown.
"""
from crewai import Agent, Task, Crew, Process


REPORT_PROMPTS = {
    "battlecard": """Generate a competitive intelligence **battlecard** in Markdown for "{subject_name}" ({subject_type}).

Structure the battlecard with these sections:
# {subject_name} — Competitive Battlecard

## Overview
Brief company/product/service description based on the analysis.

## Key Strengths
Bulleted list of competitive strengths identified.

## Key Weaknesses / Vulnerabilities
Bulleted list of weaknesses or areas of concern.

## Recent Signals & Changes
What's changed recently? New hires, pricing changes, product updates, etc.

## Competitive Positioning
How does this entity position itself? What markets/segments are they targeting?

## Recommendations
What actions should we take based on this intelligence?

## Sources Analyzed
List the sources that contributed to this analysis.
""",
    "summary": """Generate a concise **executive summary** in Markdown for "{subject_name}" ({subject_type}).

Keep it to 1-2 pages. Focus on:
- What is this entity and what do they do?
- What are the most important recent developments?
- What competitive signals should leadership be aware of?
- What are the top 3 recommended actions?
""",
    "executive_brief": """Generate a **1-page executive brief** in Markdown for "{subject_name}" ({subject_type}).

Maximum 500 words. Hit only the highest-priority points:
- One-line description
- Top 3 findings
- Top 3 signals
- Immediate recommended action
""",
}


def _build_report_prompt(
    subject_name: str, subject_type: str, analysis_data: dict, report_type: str
) -> str:
    template = REPORT_PROMPTS.get(report_type, REPORT_PROMPTS["battlecard"])
    prompt = template.format(subject_name=subject_name, subject_type=subject_type)

    prompt += f"""

--- ANALYSIS DATA ---

**Summary:**
{analysis_data.get('summary', 'No summary available.')}

**Key Findings:**
{_format_findings(analysis_data.get('key_findings', []))}

**Signals:**
{_format_signals(analysis_data.get('signals', []))}
"""
    return prompt


def _format_findings(findings: list) -> str:
    if not findings:
        return "None identified."
    lines = []
    for f in findings:
        if isinstance(f, dict):
            lines.append(f"- [{f.get('severity', '?')}] {f.get('finding', '?')} (from: {f.get('source_key', '?')})")
        else:
            lines.append(f"- {f}")
    return "\n".join(lines)


def _format_signals(signals: list) -> str:
    if not signals:
        return "None identified."
    lines = []
    for s in signals:
        if isinstance(s, dict):
            lines.append(f"- [{s.get('confidence', '?')}] {s.get('signal_type', '?')}: {s.get('description', '?')}")
        else:
            lines.append(f"- {s}")
    return "\n".join(lines)


def run_quill_report(
    subject_name: str,
    subject_type: str,
    analysis_data: dict,
    report_type: str = "battlecard",
) -> dict:
    """
    Run the Quill report agent. Returns dict with title and content_markdown.
    SYNCHRONOUS function (CrewAI kickoff is sync).
    """
    prompt = _build_report_prompt(subject_name, subject_type, analysis_data, report_type)

    agent = Agent(
        role="Intelligence Report Writer",
        goal=f"Generate a professional {report_type} report for {subject_name}",
        backstory=(
            "You are an expert intelligence report writer. You produce clear, actionable, "
            "well-structured reports that busy executives can scan quickly. You use Markdown "
            "formatting effectively — headers, bullets, bold for emphasis. You never pad "
            "reports with filler — every sentence earns its place."
        ),
        llm="anthropic/claude-sonnet-4-20250514",
        verbose=False,
        max_iter=2,
    )

    task = Task(
        description=prompt,
        expected_output=f"A well-formatted Markdown {report_type} report",
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()

    raw = str(result)
    title = f"{subject_name} — {report_type.replace('_', ' ').title()}"

    # Try to extract title from first markdown heading
    for line in raw.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
            break

    return {"title": title, "content_markdown": raw}
