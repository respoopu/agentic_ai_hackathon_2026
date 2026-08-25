# Agent System Prompts

This directory contains one system prompt per agent in the lifelong activity and career-exploration system for children.

## Architecture Overview

Standard flow:

**Planner → [Discovery → Compliance → Central Knowledge Base → Planner, if needed] → Guardian → Parent Approval → Broker → Activity → Child Feedback → Planner / Personal Profile**

The **Orchestrator** primarily controls routing between agents rather than performing specialist reasoning itself.

Two distinct data stores should be maintained:

- **Central Knowledge Base**: trusted information about the external world, such as activities, providers, locations, schedules, prices, and eligibility.
- **Personal Data / Child Profile**: information about the individual child, such as interests, skills, past activities, feedback, preferences, and constraints.

---

## Prompt files

- [Orchestrator Agent](orchestrator-agent.md)
- [Planner Agent](planner-agent.md)
- [Discovery Engine](discovery-engine.md)
- [Compliance Agent](compliance-agent.md)
- [Guardian Agent](guardian-agent.md)
- [Broker Agent](broker-agent.md)

