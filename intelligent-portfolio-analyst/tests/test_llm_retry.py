from groq import RateLimitError, APIConnectionError, BadRequestError

from utils.llm_retry import invoke_with_retry


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FlakyChain:
    """Fails `fail_times` times with `exception` then succeeds."""

    def __init__(self, exception, fail_times, success_content="ok"):
        self.exception = exception
        self.fail_times = fail_times
        self.success_content = success_content
        self.calls = 0

    def invoke(self, payload):
        self.calls += 1
        if self.calls <= self.fail_times:
            raise self.exception
        return FakeResponse(self.success_content)


def _rate_limit_error():
    # RateLimitError requires a response/body in real usage; a bare instance
    # via __new__ is enough to exercise isinstance-based retry logic here.
    return RateLimitError.__new__(RateLimitError)


class TestInvokeWithRetry:
    def test_succeeds_immediately_without_retrying(self, mocker):
        chain = mocker.Mock()
        chain.invoke.return_value = FakeResponse("first try")

        result = invoke_with_retry(chain, {"x": 1})

        assert result.content == "first try"
        assert chain.invoke.call_count == 1

    def test_retries_on_rate_limit_then_succeeds(self, mocker):
        mocker.patch("utils.llm_retry.time.sleep")  # don't actually sleep in tests
        chain = FlakyChain(_rate_limit_error(), fail_times=2, success_content="recovered")

        result = invoke_with_retry(chain, {}, max_attempts=3, base_delay_seconds=0.01)

        assert result.content == "recovered"
        assert chain.calls == 3

    def test_gives_up_after_max_attempts(self, mocker):
        mocker.patch("utils.llm_retry.time.sleep")
        chain = FlakyChain(_rate_limit_error(), fail_times=99)

        try:
            invoke_with_retry(chain, {}, max_attempts=2, base_delay_seconds=0.01)
            assert False, "expected RateLimitError to propagate"
        except RateLimitError:
            pass

        assert chain.calls == 2

    def test_non_retryable_error_propagates_immediately(self, mocker):
        chain = mocker.Mock()
        chain.invoke.side_effect = ValueError("not a Groq error")

        try:
            invoke_with_retry(chain, {})
            assert False, "expected ValueError to propagate"
        except ValueError:
            pass

        assert chain.invoke.call_count == 1

    def test_calls_logger_on_each_retry(self, mocker):
        mocker.patch("utils.llm_retry.time.sleep")
        chain = FlakyChain(_rate_limit_error(), fail_times=1, success_content="ok")
        log_calls = []

        invoke_with_retry(chain, {}, max_attempts=3, base_delay_seconds=0.01, logger=log_calls.append)

        assert len(log_calls) == 1
        assert "retrying" in log_calls[0].lower()
