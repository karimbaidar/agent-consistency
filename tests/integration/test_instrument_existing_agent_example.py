import runpy

import pytest

from agent_consistency import OutcomeVerificationError


def test_instrument_existing_agent_example_runs_success_path():
    namespace = runpy.run_path("examples/instrument_existing_agent/after.py")

    result, receipts = namespace["run_demo"]("settled")

    assert result["refund"]["status"] == "settled"
    assert receipts[-1].status == "passed"


def test_instrument_existing_agent_example_blocks_pending_refund():
    namespace = runpy.run_path("examples/instrument_existing_agent/after.py")

    with pytest.raises(OutcomeVerificationError):
        namespace["run_demo"]("pending")

