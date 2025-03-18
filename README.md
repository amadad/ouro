# Agent Architecture for Digital Being

This directory contains the agent implementations for the Digital Being framework. The architecture follows the OpenAI Agents SDK pattern, with specialized agents for different tasks and handoffs between them.

## Agent Structure

The Digital Being uses the following agents:

### Triage Agent

- **Purpose**: Primary decision-maker that determines what activity to perform next
- **Capabilities**: Analyzes context, personality, and recent actions to decide what to do
- **Handoffs**: Can delegate to specialized agents for specific tasks

### Twitter Agent

- **Purpose**: Handles Twitter posting and media generation
- **Capabilities**: Generates tweet text, determines when to include images, posts to Twitter
- **Tools**: Uses image generation and Twitter posting tools

### Thought Agent

- **Purpose**: Generates philosophical reflections and thoughts
- **Capabilities**: Creates thoughtful content based on character personality and preferences
- **Tools**: Stores and recalls memories to maintain consistency

## Agent Creation

Agents are created based on the character configuration (from character.json), which defines:

- Personality traits that influence agent behavior
- Preferences that guide content generation
- Activity constraints that determine energy costs and cooldowns
- Skill configurations for external integrations

## OpenAI Agents SDK Integration

The architecture follows these OpenAI Agents SDK patterns:

- **Agent-to-agent handoffs**: For specialized task delegation
- **Function tools**: For concrete actions like posting tweets and storing memories
- **Context passing**: To maintain state between agent runs
- **Tracing**: For observability and debugging

## Usage

To use these agents, import them from the main module:

```python
from agents import create_triage_agent, create_twitter_agent, create_thought_agent
```

Then create them with the character configuration:

```python
triage_agent = create_triage_agent(character_config)
```

Run the triage agent to start the decision-making process:

```python
result = await Runner.run(triage_agent, prompt, context=context)
```

The triage agent will automatically handle handoffs to specialized agents as needed.