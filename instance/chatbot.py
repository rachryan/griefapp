# chatbot.py — Compassionate Grief Support Chatbot (hardened)
from __future__ import annotations
import random
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class BotConfig:
    deterministic: bool = False  # set True for tests/demos
    locale_hint: str = "US/CA"   # placeholder if you localize crisis copy later

class GriefSupportBot:
    def __init__(self, config: Optional[BotConfig] = None):
        self.cfg = config or BotConfig()
        if self.cfg.deterministic:
            random.seed(42)

        # --- Response bank ---
        self.responses: Dict[str, List[str]] = {
            "greeting": [
                "Hello—I’m here with you. How are you feeling right now?",
                "Welcome. This is a safe space to share what’s on your heart. How are you doing today?",
                "Hi. I’m here to listen. What feels heaviest at the moment?"
            ],
            "feeling_bad": [
                "I’m hearing a lot of pain. Grief can feel like it takes over everything. What’s been most intense today?",
                "That sounds really hard. Your feelings make sense after a loss. Do you want to say more about what’s coming up?",
                "It’s okay to not be okay. If you can, tell me what’s underneath the sadness right now."
            ],
            "feeling_better": [
                "I’m glad there’s a bit of ease. Grief comes in waves; it’s okay to let this calmer moment be real.",
                "Good to hear. Relief and sadness can coexist—both are valid. What helped a little today?",
                "Noticing a better moment matters. What seems to support you when it shows up?"
            ],
            "memories": [
                "Thank you for sharing that. What’s a memory that feels especially alive right now?",
                "Holding onto their stories can be grounding. What was one of their quirks you loved?",
                "I’m honored you shared that. What qualities of theirs do you carry with you?"
            ],
            "sleep_issues": [
                "Sleep can get disrupted by grief. Would a simple wind-down—dim lights, light reading, slow breaths—be worth trying tonight?",
                "Not sleeping makes everything harder. Some people jot down looping thoughts before bed—could that help you?",
                "If this keeps up, talking with a clinician might help. For now, even a brief rest routine can be gentler on your system."
            ],
            "anniversary": [
                "Dates can reopen the ache. Would a small ritual—lighting a candle, visiting a place, sharing a story—feel supportive?",
                "Milestones are tender. Creating a new tradition to honor them can help hold the day.",
                "It’s natural for emotions to rise around anniversaries. Is there someone you’d want beside you that day?"
            ],
            "guilt": [
                "Guilt shows up for many people after a loss. Relationships are imperfect; love isn’t measured by flawless choices.",
                "You sound very hard on yourself. If a friend said this to you, what compassion would you offer them?",
                "‘If only’ thoughts are common and painful. We can explore them gently if you’d like."
            ],
            "anger": [
                "Anger is a valid part of grief. It can point to what mattered deeply. How does it show up in your body?",
                "Your anger makes sense. Is there a safe way to let it move—writing, movement, or hitting a pillow?",
                "Many feel uneasy with anger, but it’s normal after loss. We can sit with it here."
            ],
            "self_care": [
                "Small, doable care counts. A glass of water, a short walk, or stepping outside can be enough for now.",
                "What’s one tiny act of care you could manage in the next hour?",
                "Self-care in grief can be permission to feel, rest, and do less. What might that look like today?"
            ],
            "support": [
                "Having company helps. Who in your world can simply listen without fixing?",
                "It’s okay to ask for specific help. What would be most useful—meals, child care, a check-in call?",
                "Peer groups can help you feel less alone. Would you like ideas on how to find one?"
            ],
            "professional_help": [
                "A grief-informed therapist can offer steadiness and tools. Want a few ways to search?",
                "Professional support can widen your coping options—telehealth is common if that’s easier.",
                "If you’re open to it, we can outline what a first session might look like."
            ],
            "default": [
                "Thank you for sharing. What feels most challenging right now?",
                "I’m here. Would you like to tell me a bit more about what you’re experiencing?",
                "Grief is complex. Where does it tend to hit the hardest for you?"
            ],
            "crisis": [
                "I’m really glad you told me. You deserve immediate support. If you’re in danger or thinking of harming yourself, please call local emergency services now. If you’re in the U.S. or Canada, you can dial 988 for the Suicide & Crisis Lifeline. If possible, reach out to someone you trust to stay with you. I’ll stay with you here, too. Can you tell me where you are and if you’re safe right now?"
            ]
        }

        # Optional follow-ups per category (picked sparingly)
        self.followups: Dict[str, List[str]] = {
            "feeling_bad": ["When did you first notice today’s dip?", "Where do you feel it in your body?"],
            "memories": ["Would you like to share a photo or another story sometime?", "How do you like to honor them day-to-day?"],
            "guilt": ["What part of this guilt feels the loudest?", "If you rewind that moment, what need were you trying to meet?"],
            "anger": ["Is there a safe outlet that has helped before?", "What does the anger want you to protect?"],
            "self_care": ["What’s one tiny step you could take in the next ten minutes?", "Who could text you a check-in later today?"],
        }

        # --- Pattern bank (precompiled) ---
        def c(p: str) -> re.Pattern:
            return re.compile(p, re.IGNORECASE)

        self.patterns: Dict[str, re.Pattern] = {
            "greeting": c(r"\b(hello|hi|hey|greetings)\b"),
            "feeling_bad": c(r"\b(sad|depressed|overwhelmed|exhausted|tired|down|lonely|alone|lost|cry(?:ing)?|tears|difficult|hard)\b"),
            "feeling_better": c(r"\b(better|good|okay|ok|fine|alright|improving|hopeful|positive)\b"),
            "memories": c(r"(?:\bmemory\b|\bmemories\b|\bremember(?:ed)?\b|\bmiss(?:ing)?\b|loved\s+one)"),
            "sleep_issues": c(r"\b(sleep|insomnia|nightmares?|dreams?|awake|bed)\b"),
            "anniversary": c(r"\b(anniversary|birthday|holiday|christmas|thanksgiving|special\s+day|year\s+since|month\s+since)\b"),
            "guilt": c(r"(?:\bguilt(?:y)?\b|\bblame(?:d)?\b|\bfault\b|\bregret\b|should(?:\s+have)?|could(?:\s+have)?|would(?:\s+have)?|\bif only\b|\bsorry\b)"),
            "anger": c(r"\b(angry|anger|mad|unfair|cruel|hate|resent(?:ment)?)\b"),
            "self_care": c(r"(?:self[-\s]?care|take\s+care|help\s+myself|\b(shower|eat|eating|food|exercise|walk)\b)"),
            "support": c(r"\b(support|friend[s]?|family|help|talk(?:ing)?|listen(?:ing)?)\b"),
            "professional_help": c(r"\b(therapy|therapist|counsel(?:l)?ing|counsel(?:l)?or|professional|doctor|psychologist|psychiatrist)\b"),
        }

        # Suicide / self-harm crisis patterns (evaluated first)
        self.crisis_pattern = c(
            r"(?:suicid(?:e|al)|kill myself|end my life|can'?t go on|don'?t want to live|self[-\s]?harm|hurt myself|take my life)"
        )

        # Category priorities (higher first)
        self.priorities = [
            "crisis",
            "anniversary",
            "sleep_issues",
            "feeling_bad",
            "guilt",
            "anger",
            "memories",
            "self_care",
            "support",
            "professional_help",
            "feeling_better",
            "greeting",
            "default",
        ]

        # Track recent reply usage per category (reduce repetition)
        self._used_indexes: Dict[str, set] = {}

    # --- Public API ---
    def get_response(self, message: str) -> Dict[str, str]:
        text = (message or "").strip()
        if not text:
            return self._pack("default", "I’m here. Say anything that feels manageable to share.")

        # Crisis check first
        if self.crisis_pattern.search(text):
            return self._pack("crisis", self._choose("crisis"), matched="crisis")

        # Allow multiple category hits, then pick by priority
        hits = self._match_categories(text)
        category = self._pick_by_priority(hits) if hits else "default"

        # Smart self-care suggestion if explicitly asked
        if self._explicit_help_request(text):
            suggestion = self._get_self_care_suggestion(text)
            return self._pack("self_care", suggestion, matched="self_care(help)")

        base = self._choose(category)
        fu = self._choose_followup(category)
        reply = f"{base} {fu}" if fu else base
        return self._pack(category, reply, matched=",".join(sorted(hits)) if hits else "")

    # --- Internals ---
    def _match_categories(self, text: str) -> set:
        hits = set()
        for cat, pat in self.patterns.items():
            if pat.search(text):
                hits.add(cat)
        return hits

    def _pick_by_priority(self, hits: set) -> str:
        for cat in self.priorities:
            if cat in hits:
                return cat
        return "default"

    def _explicit_help_request(self, text: str) -> bool:
        return re.search(r"\b(suggest|recommendation|advice|tip|help|idea|what\s+(?:can|should)\s+i\s+do)\b", text, re.IGNORECASE) is not None

    def _choose(self, category: str) -> str:
        bank = self.responses.get(category, self.responses["default"])
        used = self._used_indexes.setdefault(category, set())
        choices = [i for i in range(len(bank)) if i not in used]
        if not choices:
            used.clear()
            choices = list(range(len(bank)))
        idx = choices[0] if self.cfg.deterministic else random.choice(choices)
        used.add(idx)
        return bank[idx]

    def _choose_followup(self, category: str) -> str:
        bank = self.followups.get(category)
        if not bank:
            return ""
        return bank[0] if self.cfg.deterministic else random.choice(bank)

    def _pack(self, category: str, text: str, matched: str = "") -> Dict[str, str]:
        return {"text": text, "category": category, "matched_terms": matched}

    # --- Self-care suggestions ---
    def _get_self_care_suggestion(self, message: str) -> str:
        m = message.lower()
        if re.search(r"\b(tired|sleep|eat|food|body|physical|exercise|walk|shower)\b", m):
            cat = "physical"
        elif re.search(r"\b(people|talk|friend|family|social|alone|lonely|connection)\b", m):
            cat = "social"
        elif re.search(r"\b(meaning|purpose|spiritual|faith|belief|meditation|nature|soul)\b", m):
            cat = "spiritual"
        elif re.search(r"\b(tasks|work|chores|overwhelmed|organize|decision|decide)\b", m):
            cat = "practical"
        else:
            cat = "emotional"

        recs = self._self_care_recs()[cat]
        suggestion = recs[0] if self.cfg.deterministic else random.choice(recs)
        return f"It sounds like you could use support. {suggestion} Would you like another suggestion?"

    def _self_care_recs(self) -> Dict[str, List[str]]:
        return {
            "physical": [
                "Try a two-minute body scan and slow breathing; even brief regulation helps your nervous system.",
                "A short walk or gentle stretch can release some of the tension grief holds.",
                "Hydrate and eat something simple; basics matter when energy is low.",
                "If you can, set a small wind-down routine tonight (lights down, no phone, one calming page)."
            ],
            "emotional": [
                "Let feelings move without judging them—naming them softly can reduce their intensity.",
                "A few lines of journaling about ‘what hurts most’ can bring relief.",
                "It’s okay to feel moments of ease; they don’t erase your love."
            ],
            "social": [
                "Text one trusted person: ‘Could you check in on me later? I’m having a rough day.’",
                "Ask for one concrete thing (a call, a walk, a meal) instead of ‘anything.’"
            ],
            "spiritual": [
                "If it helps, light a candle or sit in nature for five minutes and breathe with what’s here.",
                "A brief mindfulness practice—counting five things you can see/hear/feel—can ground you."
            ],
            "practical": [
                "Break today into the next tiny step; set a 10-minute timer and stop when it dings.",
                "Defer big decisions; grief narrows focus—give yourself time."
            ],
        }

# Optional: quick manual test
if __name__ == "__main__":
    bot = GriefSupportBot(BotConfig(deterministic=True))
    tests = [
        "hi",
        "I feel exhausted and can’t sleep",
        "today is his birthday and I miss him",
        "I feel so guilty, I should have done more",
        "Honestly, I don't want to live like this",
        "any tip to help right now?"
    ]
    for t in tests:
        print(t, "->", bot.get_response(t))
