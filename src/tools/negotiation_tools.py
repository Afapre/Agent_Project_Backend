from __future__ import annotations

import json
from langchain.tools import tool


def create_prompt_driven_negotiation_tools(llm_client=None) -> list:
    """Create Clara's negotiation tools powered by specialized system prompts."""

    @tool
    def negotiation_prompt_tool(
        action: str,
        supplier_name: str,
        category: str = "",
        offer_text: str = "",
        concession_type: str = "",
        concession_value: str = "",
        context_text: str = ""
    ) -> str:
        """Executes negotiation intelligence tasks by dispatching specialized system prompts 
        for playbooks, BATNA analysis, real-time counter-offers, concession tracking, and tone detection.

        Args:
            action: The prompt module to execute. Options: 
                ['playbook', 'batna', 'counter_offer', 'track_concession', 'analyze_tone']
            supplier_name: Name of the supplier involved.
            category: Commodity or product category (used for playbook generation).
            offer_text: Latest supplier quote, email, or transcript (used for counter-offers and tone analysis).
            concession_type: Type of concession made (used for tracking).
            concession_value: Magnitude or description of the concession.
            context_text: Additional context or alternative options (used for BATNA evaluation).
        """
        action_lower = action.lower().strip()
        
        # Define specialized system prompts for each negotiation workflow
        prompts = {
            "playbook": (
                f"You are Clara's Negotiation Playbook Module. Generate a proven tactical playbook "
                f"for negotiating with supplier '{supplier_name}' in the category '{category}'. "
                f"Provide: (1) Recommended opening positions, (2) Concession strategies (e.g., volume tiers, incoterms, payment terms), "
                f"and (3) Walk-away price benchmarks based on standard procurement frameworks."
            ),
            "batna": (
                f"You are Clara's BATNA Calculator. Analyze the alternatives for supplier '{supplier_name}' "
                f"given the following context/alternatives: '{context_text}'. Quantify the Best Alternative to a "
                f"Negotiated Agreement, rate the negotiating posture strength (0-100), and state the best fallback option."
            ),
            "counter_offer": (
                f"You are Clara's Real-Time Counter-Offer Generator. Review the supplier's latest offer/message from '{supplier_name}':\n\n"
                f"\"{offer_text}\"\n\n"
                f"Generate a data-backed counter-offer with clear justification drawn from market benchmarks and procurement policy. "
                f"Propose structural alternatives (payment terms, volume tiers, or incoterms) if unit prices are rigid."
            ),
            "track_concession": (
                f"You are Clara's Concession Tracker. Log the latest concession involving '{supplier_name}'. "
                f"Concession Type: {concession_type}, Details/Value: {concession_value}. "
                f"Evaluate the bilateral concession balance: ensure we are not giving away more than we receive, "
                f"and provide an immediate warning if the pattern favors the supplier unfavorably."
            ),
            "analyze_tone": (
                f"You are Clara's Emotion & Tone Analysis Module. Analyze the following text thread or transcript "
                f"from supplier '{supplier_name}':\n\n\"{offer_text}\"\n\n"
                f"Detect supplier frustration, urgency, and confidence signals. Provide actionable advice on negotiation timing "
                f"(e.g., when to push harder vs. when to offer an olive branch)."
            )
        }

        if action_lower not in prompts:
            return json.dumps({
                "error": f"Invalid action '{action}'. Choose from: {list(prompts.keys())}"
            })

        selected_system_prompt = prompts[action_lower]

        if llm_client:
            try:
                response = llm_client.invoke(selected_system_prompt)
                return json.dumps({"action": action_lower, "supplier": supplier_name, "result": response}, indent=2)
            except Exception as exc:
                return json.dumps({"error": str(exc)})

        # Default fallback: Return the structured system prompt package for Clara to execute
        return json.dumps({
            "status": "success",
            "action": action_lower,
            "supplier_name": supplier_name,
            "dispatched_system_prompt": selected_system_prompt,
            "instruction": "Execute the above system prompt using your internal reasoning and context."
        }, indent=2)

    return [negotiation_prompt_tool]