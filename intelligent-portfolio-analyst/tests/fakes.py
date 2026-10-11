"""Shared test doubles for mocking ChatGroq/yfinance in agent tests."""
from langchain_core.runnables import Runnable


class FakeLLM(Runnable):
    """
    Drop-in replacement for ChatGroq usable in a LangChain `prompt | llm`
    chain. Returns a fixed `.content` string regardless of the prompt, or
    cycles through `responses` in order if given a list, so a test can
    script a sequence of answers (e.g. fundamental verdict, technical
    verdict, final synthesis).
    """

    def __init__(self, content=None, responses=None):
        if responses is not None:
            self._responses = list(responses)
        elif content is not None:
            self._responses = [content]
        else:
            raise ValueError("FakeLLM requires either `content` or `responses`.")
        self._index = 0

    def invoke(self, input, config=None, **kwargs):
        content = self._responses[min(self._index, len(self._responses) - 1)]
        self._index += 1

        class _Response:
            pass

        response = _Response()
        response.content = content
        return response
