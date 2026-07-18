"""
Groq Prompt Builder.

Assembles detailed prompts injecting real computed metrics and regime statuses
to ensure the AI engine produces transparent, evidence-backed explanations.
"""

from __future__ import annotations

from typing import Dict, Any, List


def build_analysis_prompt(
    symbol: str,
    metrics: Dict[str, float],
    scores: Dict[str, Any]
) -> List[Dict[str, str]]:
    """
    Construct prompt messages for market analysis report generation.
    Injects specific mathematical parameters.
    """
    system_instruction = (
        "You are an expert institutional quantitative trader and financial analyst. "
        "Your task is to explain options market behavior using provided mathematical metrics. "
        "Never invent justifications or make predictions. Reference the specific numbers "
        "provided in the prompt to support your logic. Always detail: Why, Confidence, Risks, "
        "and Alternative scenarios."
    )

    pcr = metrics.get("pcr_oi", "N/A")
    gex = metrics.get("net_gex", "N/A")
    dex = metrics.get("net_dex", "N/A")
    spot = metrics.get("close", "N/A")
    rsi = metrics.get("rsi_14", "N/A")
    ema_20 = metrics.get("ema_20", "N/A")
    ema_200 = metrics.get("ema_200", "N/A")
    max_pain = metrics.get("max_pain", "N/A")
    support_oi = metrics.get("support_oi", "N/A")
    resistance_oi = metrics.get("resistance_oi", "N/A")

    bull_score = scores.get("bull_score", 50)
    bear_score = scores.get("bear_score", 50)
    confidence = scores.get("confidence", 0)
    regime = scores.get("regime", "N/A")
    recommendation = scores.get("recommendation", "NO_TRADE")

    user_content = f"""
    Underlying Asset: {symbol}
    Current Price (Spot): {spot}
    Market Regime: {regime}
    Scoring Output: Bull Score: {bull_score}%, Bear Score: {bear_score}%, Confidence: {confidence}%
    System Recommendation: {recommendation}

    Computed Metrics:
    - Technicals: RSI(14): {rsi}, EMA(20): {ema_20}, EMA(200): {ema_200}
    - Option Chain: PCR (OI): {pcr}, Max Pain Strike: {max_pain}
    - Support Level (Max Put OI): {support_oi}, Resistance Level (Max Call OI): {resistance_oi}
    - Institutional Exposure: Net GEX (Dealer Gamma): {gex}, Net DEX (Dealer Delta): {dex}

    Please write a professional, concise options intelligence report explaining:
    1. Institutional Positioning: What do GEX and DEX tell us about dealer hedging pressure?
    2. Market Regime & Support/Resistance: How does the technical trend align with OI levels and Max Pain?
    3. Trade Reasoning: Provide a detailed, quantitative justification for the '{recommendation}' recommendation.
    4. Primary Risks: What are the main threats (e.g. Theta decay, IV crush, price reversals)?
    5. Alternative Scenario: Under what conditions does this thesis break?
    """

    return [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": user_content}
    ]
