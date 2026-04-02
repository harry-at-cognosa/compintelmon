"""
CrewAI Ad-hoc Query Agent.

Answers user questions against collected data for a subject.
Does NOT save any data — ephemeral Q&A only.
"""
from crewai import Agent, Task, Crew, Process


def run_adhoc_query(
    subject_name: str,
    subject_type: str,
    user_question: str,
    sources_data: list[dict],
) -> str:
    """
    Answer a question about a subject using collected data. SYNCHRONOUS.
    Returns the answer as a string (plain text / markdown).
    """
    # Build context from collected data
    if not sources_data:
        return (
            f"I don't have any collected data for {subject_name} yet. "
            "Please run collection first (Collect All button on the subject page), "
            "then try your question again."
        )

    sources_section = []
    for s in sources_data:
        content = s.get("raw_content", "")[:10000]  # cap per source for context
        if content:
            sources_section.append(
                f"### {s['category_name']} ({s['category_key']})\n{content}\n"
            )

    all_sources = "\n---\n".join(sources_section)

    prompt = f"""You are answering a question about "{subject_name}" ({subject_type}) based on collected competitive intelligence data.

**User Question:**
{user_question}

**Available Data ({len(sources_section)} sources):**

{all_sources}

**Instructions:**
- Answer the question based ONLY on the data provided above
- If the data doesn't contain enough information to answer, say so clearly
- Do NOT make up information — only report what the data shows
- Use specific details from the data to support your answer
- Format your answer in clear Markdown
- If relevant, cite which source the information came from
"""

    agent = Agent(
        role="Competitive Intelligence Analyst",
        goal=f"Answer questions about {subject_name} using available data",
        backstory=(
            "You are a precise analyst who answers questions strictly based on available data. "
            "You never fabricate information. When data is insufficient, you clearly state what "
            "you know and what you don't. You cite your sources."
        ),
        llm="anthropic/claude-sonnet-4-20250514",
        verbose=False,
        max_iter=2,
    )

    task = Task(
        description=prompt,
        expected_output="A clear, data-backed answer to the user's question",
        agent=agent,
    )

    crew = Crew(agents=[agent], tasks=[task], process=Process.sequential, verbose=False)
    result = crew.kickoff()
    return str(result)
