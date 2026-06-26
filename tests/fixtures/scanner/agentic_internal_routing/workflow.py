from agent_framework import WorkflowContext


class AgentWorkflowState:
    def advanced(self, agent_name):
        return self


async def route_between_agents(state: AgentWorkflowState, ctx: WorkflowContext):
    await ctx.send_message(state.advanced("SpecialistAgent"))
