# Agent Specification

## Project name

**Kopilkin Multi-Agent Financial Assistant**

## Purpose

The agent system helps Kopilkin users understand their personal spending, identify major expense categories, and receive practical saving advice based on their real transaction data.

## User problem

Users often record expenses but do not immediately understand where their money goes or how to improve their financial habits. The agent transforms raw transaction data into understandable insights and advice.

## Agents

### 1. Orchestrator Agent

**Responsibility:** coordinates the whole multi-agent flow.

Main tasks:

- Receives the user's message.
- Searches long-term memory.
- Enriches the current message with relevant previous context.
- Routes the request to Analyst or Advisor.
- Saves the final interaction into memory.

### 2. Router Agent

**Responsibility:** decides which agent path should be used.

Routes:

- `analyst` - when the user asks about numbers, categories, totals, or spending analysis.
- `advisor` - when the user asks for recommendations or saving advice.

### 3. Analyst Agent

**Responsibility:** retrieves and analyzes real transaction data.

Main tasks:

- Calls Transaction Service.
- Gets total income, total expenses, and category breakdown.
- Explains where the user's money goes.
- Uses actual numbers instead of invented data.

### 4. Advisor Agent

**Responsibility:** gives practical and realistic financial advice.

Main tasks:

- Uses the Analyst Agent result as context.
- Suggests concrete saving steps.
- References real user numbers.
- Avoids investment/trading/tax/legal advice.

## Inputs

- `user_id`: ID of the authenticated Kopilkin user.
- `message`: natural language question from the user.
- Transaction summary from Transaction Service.
- Relevant memories from Mem0/Qdrant.

## Outputs

- Natural language answer in the same language as the user.
- Financial insight or practical recommendation.
- Saved long-term memory entry.
- Langfuse trace and Prometheus metrics.

## Safety and limitations

The system does not request card details, passwords, or sensitive financial credentials. It does not provide investment, trading, tax, or legal advice. If there is not enough transaction data, the agent clearly says that more data is needed.
