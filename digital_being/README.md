# Digital Being Framework

A digital being framework using OpenAI Agents SDK and Responses API architecture.

## Architecture

The Digital Being runs on a SIFDA architecture:

- **Sense**: Receive input from the environment
- **Interpret**: Understand and contextualize input
- **Feel**: Evaluate emotional response
- **Decide**: Choose next action
- **Act**: Perform the chosen action

### Key Components

- **Agents**: Defined in `being_agents/sifda.py`, following OpenAI Agents SDK pattern
- **Tools**: Registered with decorators in `tools/` directory
- **Schema**: Data models and context in `framework/schema.py`
- **Activities**: Handlers for specific actions in `framework/activity_handlers.py`

## Getting Started

1. Set up environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Configure API Keys in `.env`:
   ```
   OPENAI_API_KEY=your_openai_key
   COMPOSIO_API_KEY=your_composio_key
   ```

3. Run the digital being:
   ```bash
   python app.py
   ```

## Extensions

- **Twitter Integration**: Post tweets with AI-generated images
- **Memory System**: Long-term storage of experiences 
- **Activity System**: Modular activities that can be extended

## Customization

Edit `character/character.json` to adjust personality, preferences, and behavior of your digital being.

## Architecture Diagram

```
┌─────────────┐       ┌─────────────┐
│   Sense     │──────▶│  Interpret  │
│  (Input)    │       │ (Thought)   │
└─────────────┘       └──────┬──────┘
                             │
                             ▼
┌─────────────┐       ┌─────────────┐
│    Act      │◀─────┐│   Decide    │◀─────┐
│ (Activities) │      │ (Triage)    │      │
└─────────────┘       └─────────────┘      │
                                           │
                      ┌─────────────┐      │
                      │    Feel     │──────┘
                      │  (Emotion)  │
                      └─────────────┘
```