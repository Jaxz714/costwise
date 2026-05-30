# CostWise

AI cost optimizer with smart model routing. Cut your AI API costs by 50-80%.

CostWise intelligently routes tasks to the cheapest capable model based on task complexity, tracks spending in real-time, and helps you optimize your AI budget.

## Features

- **Smart Model Routing**: Automatically assesses task complexity and routes to the cheapest capable model
- **Cost Dashboard**: Real-time spending breakdown by model, provider, and task type
- **Budget System**: Set monthly/daily budgets with automatic alerts at configurable thresholds
- **Savings Calculator**: See how much you saved vs using the most expensive model for everything
- **Optimization Recommendations**: Get actionable suggestions to further reduce costs
- **20+ Models**: Supports Claude, GPT, DeepSeek, Kimi/Moonshot, and Gemini models

## Installation

```bash
pip install costwise
```

## Quick Start

```bash
# Initialize configuration
costwise init

# Set a monthly budget
costwise budget set 50

# View the cost dashboard
costwise dashboard

# See available models
costwise models

# Get optimization recommendations
costwise optimize

# Check savings from smart routing
costwise savings
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `costwise init` | Setup configuration |
| `costwise dashboard` | Show cost dashboard |
| `costwise dashboard --period week` | Weekly view |
| `costwise budget set 50` | Set $50 monthly budget |
| `costwise budget status` | Check budget status |
| `costwise optimize` | Get optimization recommendations |
| `costwise models` | List all models with pricing |
| `costwise compare` | Compare provider costs |
| `costwise savings` | Show savings from smart routing |
| `costwise route "task"` | Route a task to optimal model |
| `costwise history` | Show recent usage history |

## Python Library Usage

```python
from costwise import Router

# Create a router
router = Router()

# Choose the best model for a task
decision = router.choose("summarize this article about AI")

print(f"Complexity: {decision.complexity.value}")
print(f"Chosen model: {decision.chosen_model.display_name}")
print(f"Estimated cost: ${decision.estimated_cost:.4f}")
print(f"Potential savings: ${decision.potential_savings:.4f}")
```

## How It Works

### Task Complexity Classification

CostWise uses keyword and pattern matching (not another LLM call) to classify tasks:

- **Simple**: "summarize", "translate", "format", "list", "what is" → cheapest models
- **Medium**: "explain", "compare", "analyze", "write" → mid-tier models
- **Complex**: "code", "architect", "debug", "design", "reason" → best models

### Smart Routing

Based on complexity, CostWise selects the optimal model considering:

- Cost (50% weight): Lower price preferred
- Quality (30% weight): Higher quality preferred for complex tasks
- Speed (20% weight): Faster models preferred when quality is similar

### Supported Models

| Provider | Models |
|----------|--------|
| Anthropic | Claude Haiku 4.5, Claude Sonnet 4.6, Claude Opus 4.8 |
| OpenAI | GPT-5.4 Nano, GPT-5.4 Mini, GPT-5.4, GPT-5.5 |
| DeepSeek | DeepSeek V4 Flash, DeepSeek V4 Pro |
| Moonshot | Kimi K2.6 |
| Google | Gemini 3.1 Flash-Lite, Gemini 2.5 Flash, Gemini 3.5 Flash, Gemini 2.5 Pro |

## Configuration

CostWise stores configuration at `~/.costwise/`:

- `config.yaml`: User configuration overrides
- `usage.db`: SQLite database with usage history

See `config/default.yaml` for all available options.

## License

MIT License - Copyright (c) 2026 Jaxz714
