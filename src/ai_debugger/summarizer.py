"""LangChain chain that summarizes Docker error bursts into root-cause text."""
from typing import Optional

from langchain_anthropic import ChatAnthropic
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from log_monitor import ErrorBurst

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "You are an expert SRE analyzing logs from a distributed event processing system. "
            "The system has three services: 'ingress' (C++ gRPC server), 'processor' (Python Kafka consumer), "
            "and 'ai-debugger' (Python LangChain service). "
            "Given an error log excerpt, identify the root cause concisely (2-4 sentences). "
            "State: what failed, why it likely failed, and the recommended first action to resolve it. "
            "Be direct and actionable — avoid generic advice."
        ),
    ),
    (
        "human",
        (
            "Container: {container}\n\n"
            "Error log excerpt:\n```\n{logs}\n```\n\n"
            "Root cause analysis:"
        ),
    ),
])


class LogSummarizer:
    def __init__(self, api_key: str, model: str = "claude-haiku-4-5-20251001"):
        self.model = model
        self._api_key = api_key
        self._chain = None

    def build_chain(self):
        llm = ChatAnthropic(model=self.model, api_key=self._api_key, max_tokens=256)
        self._chain = _PROMPT | llm | StrOutputParser()

    def summarize(self, burst: ErrorBurst) -> str:
        if self._chain is None:
            self.build_chain()
        return self._chain.invoke({
            "container": burst.container,
            "logs": burst.summary,
        })
