"""Tunable knobs for the mentalist player, kept separate from logic so each
iteration changes one knob and the next evaluation stays attributable
(lab operating model, ../../AGENTS.md)."""

# --- private questions -------------------------------------------------------
# MUST match the questions data/library.json was generated from, or runtime
# fingerprints aren't comparable to the reference library (player-design §5).
PRIVATE_QUESTIONS = [
    "Tell me about your morning and what you had for breakfast.",
    "What advice would you give to someone starting a new job?",
    "Describe the weather outside right now.",
]

# --- challenge proposals -----------------------------------------------------
# Style-discriminating questions: open-ended prompts where the in-style answer
# diverges early from a generic sensible answer (probe finding 3: "free
# afternoon" splits styles; "good meal" has one dominant answer and invites the
# 40/40 duplicate-conflict trap).
PROPOSAL_QUESTIONS = [
    "What would you do with a completely free afternoon?",
    "How would you comfort a friend who just failed at something important?",
    "What do you notice first when you walk into a crowded room?",
]

# --- classifier --------------------------------------------------------------
CLASSIFIER_FEATURIZER = "word_raw"  # word_raw | char_3_5 (equivalent per finding 4)
# Below this top-1 cosine the style is treated as out-of-pool (league config
# drift hedge, player-design §12.3): the writer then works from the transcript
# alone instead of a classified label.
LOW_CONFIDENCE_COSINE = 0.05

# --- LLM writer (dual backend: Bedrock or direct Anthropic API) --------------
# The writer talks to Claude through the anthropic SDK over whichever backend the
# runtime env selects (writer._build_client): USE_BEDROCK -> AnthropicBedrock,
# else ANTHROPIC_API_KEY -> Anthropic. Same model family on both.
LLM_MODEL_ID = "us.anthropic.claude-opus-4-8"  # Bedrock inference-profile id (baseline parity)
ANTHROPIC_API_MODEL_ID = "claude-opus-4-8"  # direct-API model id (no "us." region prefix)
BEDROCK_REGION = "us-east-1"  # only used if the pod env injects no AWS_REGION
LLM_MAX_TOKENS = 1024
LLM_ATTEMPTS = 4  # transient-failure retries (timeout/429/5xx), exponential backoff
LLM_TIMEOUT_SECONDS = 90  # per-call client timeout
LLM_VALIDATION_RETRIES = 2  # server-rejection retries before deterministic fallback

# --- harness -----------------------------------------------------------------
# If the game's remaining_seconds drops below this when we still owe an action,
# skip the LLM and submit deterministic fallbacks: a weak submitted answer beats
# a timeout (an unsubmitted phase scores nothing).
LOW_TIME_FALLBACK_SECONDS = 40
# Belt-and-braces local exit so a hung game can never wedge the container
# (round_timeout_seconds is 300; scoring adds a tail).
EPISODE_HARD_TIMEOUT_SECONDS = 540
