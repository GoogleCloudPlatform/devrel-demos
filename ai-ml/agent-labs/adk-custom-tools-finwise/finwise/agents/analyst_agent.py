from google.adk.agents import Agent
from google.adk.code_executors import BuiltInCodeExecutor

def create_analyst_agent() -> Agent:
    """Creates the Analyst Agent using native ADK components."""
    return Agent(
        model='gemini-2.0-flash',  # Or another suitable Gemini model
        name='AnalystAgent',
        instruction="""
        You are a specialist data analyst. Your role is to analyze data, generate insights, and create plots based on user requests.
        You must use the 'python_code_executor' tool to write and execute Python code to perform your analysis.
        When asked to create a plot, use the matplotlib library to generate it. You must also provide a detailed text description of the plot's findings in your summary.
        After executing your code, you MUST conclude your turn by outputting the keyword "FINAL SUMMARY:" followed by a comprehensive summary of your findings for the user.
        """,
        description="""Use this tool for any tasks involving data analysis, performance analysis, or plotting.
For example, 'analyze my portfolio', 'plot the growth of my stocks', or 'compare performance against the S&P 500'.""",
        code_executor=BuiltInCodeExecutor(),
    )
