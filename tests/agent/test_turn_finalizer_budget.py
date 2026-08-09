from unittest.mock import MagicMock, patch

from agent.iteration_budget import IterationBudget
from agent.turn_finalizer import finalize_turn


def _budget_exhausted_agent():
    agent = MagicMock()
    agent.max_iterations = 100
    agent.quiet_mode = True
    agent.iteration_budget = IterationBudget(100)
    for _ in range(100):
        assert agent.iteration_budget.consume() is True
    agent.model = "test-model"
    agent.provider = "test-provider"
    agent.base_url = "https://example.invalid/v1"
    agent.session_id = "test-session"
    agent.context_compressor = MagicMock(last_prompt_tokens=0)
    agent._tool_guardrail_halt_decision = None
    agent._response_was_previewed = False
    agent._skill_nudge_interval = 0
    agent._iters_since_skill = 0
    agent.valid_tool_names = []
    agent.session_input_tokens = 0
    agent.session_output_tokens = 0
    agent.session_cache_read_tokens = 0
    agent.session_cache_write_tokens = 0
    agent.session_reasoning_tokens = 0
    agent.session_prompt_tokens = 0
    agent.session_completion_tokens = 0
    agent.session_total_tokens = 0
    agent.session_estimated_cost_usd = 0.0
    agent.session_cost_status = "unknown"
    agent.session_cost_source = "test"
    agent._drain_pending_steer.return_value = None
    agent._format_file_mutation_failure_footer.side_effect = lambda text: text
    agent._turn_failed_file_mutations = {}
    agent._turn_completion_explainer_enabled.return_value = False
    agent._interrupt_message = None
    return agent


def test_budget_exhaustion_is_incomplete_without_summary_call():
    agent = _budget_exhausted_agent()

    with patch("hermes_cli.plugins.invoke_hook"):
        result = finalize_turn(
            agent,
            final_response=None,
            api_call_count=100,
            interrupted=False,
            failed=False,
            messages=[{"role": "user", "content": "do work"}],
            conversation_history=[],
            effective_task_id="task-1",
            turn_id="turn-1",
            user_message="do work",
            original_user_message="do work",
            _should_review_memory=False,
            _turn_exit_reason="loop_stopped",
        )

    agent._handle_max_iterations.assert_not_called()
    assert result["completion_status"] == "incomplete"
    assert result["completed"] is False
    assert result["continuation_eligible"] is True
    assert result["budget_exhausted"] is True
    assert result["budget_used"] == 100
    assert result["budget_max"] == 100
    assert result["turn_id"] == "turn-1"
    assert "No summary was generated" in result["final_response"]
    assert "asking model to summarise" not in result["final_response"]
