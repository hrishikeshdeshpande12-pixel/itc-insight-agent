import os
import re
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path
from google import genai
from google.genai import types

import google.adk as adk
from app.config import settings
from app.agent.tools import ITCAgentTools
from app.agent.prompts import (
    ITC_SYSTEM_PROMPT,
    ITC_SYNTHESIS_PROMPT,
    ITC_WEB_SYNTHESIS_PROMPT,
    ITC_OUT_OF_SCOPE_MESSAGE
)
from app.models.response import ChatResponse, Citation
from app.utils.logging import get_logger

logger = get_logger("agent.core")

# Keywords that explicitly request real-time or current market news outside annual reports
WEB_TRIGGER_KEYWORDS = {
    "latest share price", "current stock price", "today's price",
    "today's stock", "current market cap", "recent announcement",
    "latest acquisition", "current ceo", "today's news", "live price",
    "current price", "stock quote", "nse price", "bse price"
}

# Core entities and terms belonging to ITC Limited ecosystem
ITC_CORE_KEYWORDS = {
    "itc", "itc's", "itc-", "aashirvaad", "sunfeast", "bingo", "yippee", "yi ppee",
    "fiama", "vivel", "savlon", "engage", "classmate", "paperkraft", "mangaldeep",
    "dermafique", "charmis", "nimyle", "nimwash", "b natural", "fabelle",
    "sunbean", "gumon", "candyman", "mint-o", "superia", "homelites",
    "sanjiv puri", "puri", "e-choupal", "echoupal", "paperboards", "bhadrachalam",
    "itc next", "sustainability 2.0", "triple bottom line", "value creation model",
    "fmcg", "cigarette", "tobacco", "hotels demerger", "itc hotels", "agri-business",
    "cmd presentation", "viksit bharat"
}

# Regex patterns matching queries explicitly asking about off-topic domains (weather, sports, politics, etc.)
OFF_TOPIC_PATTERNS = [
    r"\b(weather|temperature|forecast|rain|rainfall|monsoon|climate\s+in|humidity)\b",
    r"\b(cricket|football|fifa|ipl|world\s+cup|messi|ronaldo|virat\s+kohli|rohit\s+sharma)\b",
    r"\b(trump|biden|modi|putin|election|parliament|congress\s+party|bjp|politics)\b",
    r"\b(recipe|how\s+to\s+cook|ingredients\s+for|how\s+to\s+make\s+(?:a\s+)?(?:cake|pizza|pasta|biryani|tea|coffee))\b",
    r"\b(python\s+code|javascript|write\s+a\s+function|react\s+component|leetcode|debug\s+my\s+code)\b",
    r"\b(capital\s+of|distance\s+between|population\s+of|tallest\s+mountain|deepest\s+ocean)\b",
    r"\b(movie|actor|actress|bollywood|hollywood|box\s+office|song|singer|celebrity)\b"
]

# Follow-up conversational keywords referring to the previous answer
FOLLOW_UP_PATTERNS = [
    r"\b(explain\s+(this|it|to\s+me)?\s*(in\s+easy\s+language|in\s+simple\s+words|in\s+simple\s+terms|simply)?)\b",
    r"\b(in\s+easy\s+language|in\s+simple\s+words|in\s+simple\s+terms|simplify|simplify\s+this|make\s+it\s+simpler|make\s+it\s+easy)\b",
    r"\b(tell\s+me\s+more|elaborate|summarize|summary|break\s+it\s+down|in\s+detail|shorter|bullet\s+points|give\s+examples)\b",
    r"\b(what\s+does\s+this\s+mean|what\s+does\s+that\s+mean|why\s+is\s+this|how\s+does\s+this\s+work|can\s+you\s+clarify)\b",
    r"\b(explain\s+like|for\s+a\s+beginner|easy\s+words|simple\s+explanation|key\s+takeaways|what\s+about\s+that)\b",
    r"\b(show\s+(me\s+)?(the\s+)?(flow\s*chart|flowchart|image|images|diagram|picture|visual))\b"
]

def strip_source_citations(text: str) -> str:
    """
    Strips document file names, PDF titles, page references, and source attribution tags
    from the generated text so the response remains pure executive prose.
    """
    if not text:
        return ""

    # Remove bracketed or parenthesized citations containing .pdf, 'source:', or 'doc:'
    text = re.sub(r'(?i)\[\s*(?:source|sources|ref|reference|doc|document)?\s*:?[^\]]*?\.pdf[^\]]*?\]', '', text)
    text = re.sub(r'(?i)\(\s*(?:source|sources|ref|reference|doc|document)?\s*:?[^)]*?\.pdf[^)]*?\)', '', text)
    text = re.sub(r'(?i)\[\s*(?:source|sources|ref|reference)\s*:[^\]]*?\]', '', text)
    text = re.sub(r'(?i)\(\s*(?:source|sources|ref|reference)\s*:[^)]*?\)', '', text)

    # Remove standalone lines starting with Source: or **Source:** or *Source:*
    text = re.sub(r'(?im)^\s*(?:\*{0,2})Sources?(?:\*{0,2})\s*:[^\n]*$', '', text)

    # Remove inline "Source: ... .pdf..." or "Source: ... Page X" or "cmd_presentation.pdf, Page 8"
    text = re.sub(r'(?i)\bSources?\s*:\s*[\w\-\.\/\s]+\.pdf(?:\s*,?\s*(?:page|pg|slide)\s*\d+)?', '', text)
    text = re.sub(r'(?i)\b[\w\-_]+\.pdf(?:\s*,?\s*(?:page|pg|slide)\s*\d+)?', '', text)

    # Remove lingering page tags like "(Page 8)" or "[Page 8]" if left isolated
    text = re.sub(r'(?i)\[\s*(?:page|pg|slide)\s*\d+\s*\]', '', text)
    text = re.sub(r'(?i)\(\s*(?:page|pg|slide)\s*\d+\s*\)', '', text)

    # Clean up orphan lead-in attribution phrases like "According to," or "As stated in," left after citation removal
    text = re.sub(r'(?im)^\s*(?:according to|as reported in|as stated in|as per|as highlighted in|per)\s*,?\s*', '', text)
    text = re.sub(r'(?i)\b(?:according to|as reported in|as stated in|as per|as highlighted in)\s*,\s*', '', text)

    # Clean up empty parentheses or brackets left behind
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'\[\s*\]', '', text)

    # Clean up spaces before punctuation
    text = re.sub(r'\s+([,.;:])', r'\1', text)

    # Clean up excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def is_refusal_response(answer: str) -> bool:
    """
    Checks if a generated model response is an out-of-scope refusal, declination,
    or statement indicating the query is outside the domain of ITC Limited.
    """
    if not answer:
        return False
    ans_lower = answer.lower()
    refusal_indicators = [
        "strictly dedicated to itc",
        "dedicated exclusively to itc",
        "exclusively about itc",
        "exclusively dedicated to",
        "strictly and exclusively for itc",
        "exclusively an itc",
        "exclusively for itc",
        "outside the context of itc",
        "outside the scope of itc",
        "outside the scope of my",
        "outside the scope",
        "outside my scope",
        "outside my domain",
        "outside the domain",
        "unrelated to itc",
        "not related to itc",
        "cannot provide information about",
        "cannot provide information regarding",
        "i cannot provide information",
        "i am unable to provide",
        "i cannot answer questions",
        "i cannot assist with",
        "cannot assist with questions regarding",
        "cannot answer inquiries regarding",
        "enterprise research assistant strictly dedicated to itc",
        "enterprise intelligence research assistant dedicated exclusively",
        "only assist with inquiries regarding itc",
        "itc limited intelligence platform",
        "information exclusively about itc"
    ]
    return any(indicator in ans_lower for indicator in refusal_indicators)

class ITCAgent:
    def __init__(self, tools: Optional[ITCAgentTools] = None):
        self.tools = tools or ITCAgentTools()
        self._genai_client: Optional[genai.Client] = None
        self._adk_agent: Optional[adk.Agent] = None
        # In-memory session history storage: session_id -> list of turn dicts
        self.sessions: Dict[str, List[Dict[str, Any]]] = {}
        self._last_active_session_id: Optional[str] = None
        self._init_adk_agent()

    def _get_genai_client(self) -> genai.Client:
        if self._genai_client is None:
            self._genai_client = genai.Client(
                vertexai=True,
                project=settings.GOOGLE_CLOUD_PROJECT,
                location=settings.GOOGLE_CLOUD_LOCATION
            )
        return self._genai_client

    def _init_adk_agent(self):
        """Initializes Google ADK Agent structure with tools."""
        try:
            self._adk_agent = adk.Agent(
                name="itc_insight_advisor",
                description="Enterprise Strategy, FMCG, and Governance Advisor strictly for ITC Limited",
                instruction=ITC_SYSTEM_PROMPT,
                model=settings.GENERATION_MODEL,
                tools=[
                    self.tools.search_itc_knowledge,
                    self.tools.retrieve_itc_page,
                    self.tools.search_web_if_needed
                ]
            )
            logger.info("Google ADK Agent structure successfully initialized.")
        except Exception as e:
            logger.warning(f"ADK Agent initialization notice: {e}")

    def is_explicitly_itc_query(self, query: str) -> bool:
        """Checks if the query explicitly mentions ITC or an official ITC brand/executive/initiative."""
        q_lower = query.lower()
        return any(kw in q_lower for kw in ITC_CORE_KEYWORDS)

    def is_current_info_query(self, query: str) -> bool:
        q_lower = query.lower()
        return any(kw in q_lower for kw in WEB_TRIGGER_KEYWORDS)

    def is_explicitly_off_topic_query(self, query: str) -> bool:
        """Identifies queries explicitly asking about off-topic domains (weather, sports, general politics, recipes, coding, etc.)."""
        if self.is_explicitly_itc_query(query):
            return False
        q_lower = query.lower().strip()
        for pattern in OFF_TOPIC_PATTERNS:
            if re.search(pattern, q_lower):
                return True
        return False

    def is_conversational_follow_up(self, query: str, session_id: Optional[str]) -> bool:
        """Determines if a query is a follow-up or refinement referencing the previous ITC conversation."""
        effective_session_id = session_id or self._last_active_session_id
        if not effective_session_id or effective_session_id not in self.sessions or not self.sessions[effective_session_id]:
            return False

        # If the query is explicitly off-topic (e.g. weather, sports, general politics), never treat as a follow-up
        if self.is_explicitly_off_topic_query(query):
            return False

        q_lower = query.lower().strip()
        # Check explicit follow-up regex patterns
        for pattern in FOLLOW_UP_PATTERNS:
            if re.search(pattern, q_lower):
                return True

        # Short query with explicit pronouns or deictic references to prior context
        words = q_lower.split()
        deictic_pronouns = {"this", "that", "it", "they", "these", "those", "above", "aforesaid", "mentioned", "earlier", "previous"}
        if len(words) <= 12 and any(w in deictic_pronouns for w in words):
            return True

        # Very short conversational prompts (e.g. "why?", "how so?", "elaborate please")
        if len(words) <= 3 and any(w in {"why", "how", "elaborate", "clarify"} for w in words):
            return True

        return False

    def handle_follow_up(self, question: str, session_id: str) -> ChatResponse:
        """Synthesizes an explanation or simplification based on previous conversation turn."""
        effective_session_id = session_id or self._last_active_session_id
        if not effective_session_id or effective_session_id not in self.sessions:
            effective_session_id = f"itc_sess_{uuid.uuid4().hex[:8]}"
            self.sessions[effective_session_id] = []

        history = self.sessions.get(effective_session_id, [])
        if not history:
            return ChatResponse(
                answer="Could not find prior conversation to clarify.",
                citations=[],
                source_type="none",
                visual_context_used=False,
                session_id=effective_session_id
            )

        last_turn = history[-1]
        last_q = last_turn.get("question", "")
        last_a = last_turn.get("answer", "")
        last_citations = last_turn.get("citations", [])
        last_source_type = last_turn.get("source_type", "document")
        last_visual = last_turn.get("visual_context_used", False)
        last_related_images = last_turn.get("related_images", [])

        logger.info(f"Handling follow-up inquiry in session '{effective_session_id}': '{question}' based on previous question: '{last_q}'")

        client = self._get_genai_client()
        follow_up_prompt = f"""You are ITC Insight, an enterprise research assistant strictly dedicated to ITC Limited.
The user is asking a follow-up clarification, simplification, or elaboration regarding the previous answer about ITC Limited.

Previous Question about ITC:
{last_q}

Previous Detailed Answer:
{last_a}

User's Follow-up Request:
{question}

Instructions:
1. Address the user's request directly (for example, explaining the concept in easy, plain, everyday language, or summarizing key points, or providing step-by-step clarity).
2. Ground all explanations strictly in the verified facts from the previous ITC answer.
3. Keep the tone friendly, professional, and accessible.
4. Do not invent any new claims.
"""

        response = client.models.generate_content(
            model=settings.GENERATION_MODEL,
            contents=follow_up_prompt,
            config=types.GenerateContentConfig(
                system_instruction=ITC_SYSTEM_PROMPT,
                temperature=0.3
            )
        )

        raw_answer = response.text.strip() if response.text else "Could not generate clarification."
        answer_text = strip_source_citations(raw_answer)

        # Check if the model generated an out-of-scope domain refusal
        if is_refusal_response(answer_text):
            logger.info("Follow-up response determined to be an out-of-scope refusal. Stripping prior citations and images.")
            refusal_resp = ChatResponse(
                answer=answer_text,
                citations=[],
                source_type="none",
                visual_context_used=False,
                related_images=[],
                session_id=effective_session_id
            )
            self.sessions[effective_session_id].append({
                "question": question,
                "answer": answer_text,
                "citations": [],
                "source_type": "none",
                "visual_context_used": False,
                "related_images": []
            })
            self._last_active_session_id = effective_session_id
            return refusal_resp

        chat_resp = ChatResponse(
            answer=answer_text,
            citations=last_citations,
            source_type=last_source_type,
            visual_context_used=last_visual,
            related_images=last_related_images,
            session_id=effective_session_id
        )

        # Append turn to session history
        self.sessions[effective_session_id].append({
            "question": question,
            "answer": answer_text,
            "citations": last_citations,
            "source_type": last_source_type,
            "visual_context_used": last_visual,
            "related_images": last_related_images
        })
        self._last_active_session_id = effective_session_id

        return chat_resp

    def run(self, question: str, session_id: Optional[str] = None) -> ChatResponse:
        """Executes the Document-First Agentic RAG workflow with multimodal understanding and strict domain scoping."""
        # Auto-resolve or establish effective session identifier
        effective_session_id = session_id
        if not effective_session_id:
            if self._last_active_session_id and self.is_conversational_follow_up(question, self._last_active_session_id):
                effective_session_id = self._last_active_session_id
            else:
                effective_session_id = f"itc_sess_{uuid.uuid4().hex[:8]}"

        self._last_active_session_id = effective_session_id
        logger.info(f"Processing question: '{question}' (session: {effective_session_id})")
        client = self._get_genai_client()

        # Step 0: Check if this is a follow-up inquiry to an established session
        if self.is_conversational_follow_up(question, effective_session_id):
            return self.handle_follow_up(question, effective_session_id)

        has_explicit_itc_kw = self.is_explicitly_itc_query(question)
        is_current_info = self.is_current_info_query(question)

        # Step 0.5: Immediate check for off-topic queries (e.g. weather, sports, general politics, recipes, coding)
        # Never search documents or return citations/diagrams for queries unrelated to ITC Limited
        if not has_explicit_itc_kw and self.is_explicitly_off_topic_query(question):
            logger.warning(f"Explicit non-ITC query detected: '{question}'. Immediately declining without document search.")
            return ChatResponse(
                answer=ITC_OUT_OF_SCOPE_MESSAGE,
                citations=[],
                source_type="none",
                visual_context_used=False,
                related_images=[],
                session_id=effective_session_id
            )

        # Step 1: Real-time query evaluation
        # If user asks for live stock/news, ONLY permit web search if it pertains to ITC!
        if is_current_info:
            if has_explicit_itc_kw:
                logger.info("Query identified as requiring real-time ITC web intelligence. Invoking web search.")
                web_result = self.tools.search_web_if_needed(question)
                ans = web_result.get("text", "Information not found.")
                cits = web_result.get("citations", [])
                
                chat_resp = ChatResponse(
                    answer=ans,
                    citations=cits,
                    source_type="web",
                    visual_context_used=False,
                    session_id=effective_session_id
                )
                self.sessions.setdefault(effective_session_id, []).append({
                    "question": question, "answer": ans, "citations": cits,
                    "source_type": "web", "visual_context_used": False
                })
                return chat_resp
            else:
                logger.warning(f"Non-ITC current info query detected: '{question}'. Declining.")
                return ChatResponse(
                    answer=ITC_OUT_OF_SCOPE_MESSAGE,
                    citations=[],
                    source_type="none",
                    visual_context_used=False,
                    session_id=effective_session_id
                )

        # Step 2: Primary local ITC Knowledge Retrieval
        rag_result = self.tools.search_itc_knowledge(question)
        evidence_items = rag_result.get("evidence", [])
        citations = rag_result.get("citations", [])
        visual_images = rag_result.get("visual_images", [])

        # Step 3: Evaluate sufficiency & domain relevance
        top_score = max((e["score"] for e in evidence_items), default=0.0)
        total_content_len = sum(len(e["content"]) for e in evidence_items)

        # Strict domain relevance check:
        # If the query does NOT contain any ITC keywords AND the top retrieval score is weak (< 0.70),
        # it is an off-topic query (e.g. "who is donald trump", "capital of Italy", etc.)
        if not has_explicit_itc_kw and top_score < 0.70:
            logger.warning(f"Off-topic inquiry detected (score: {top_score:.3f}): '{question}'. Strictly declining without web fallback.")
            return ChatResponse(
                answer=ITC_OUT_OF_SCOPE_MESSAGE,
                citations=[],
                source_type="none",
                visual_context_used=False,
                session_id=effective_session_id
            )

        # Evidence is sufficient if score meets threshold and content is substantive
        is_sufficient = (top_score >= settings.RELEVANCE_THRESHOLD and total_content_len > 120)

        # Step 4: If sufficient in ITC documents, synthesize response
        if is_sufficient:
            logger.info(f"Evidence is sufficient ({len(evidence_items)} items, top score: {top_score:.3f}). Synthesizing from ITC documents.")
            
            # Prepare formatted evidence text
            evidence_text_parts = []
            visual_summaries = []
            visual_context_used = False

            for idx, item in enumerate(evidence_items, 1):
                evidence_text_parts.append(
                    f"--- Excerpt {idx} ---\n{item['content']}"
                )
                if item.get("visual_available"):
                    visual_summaries.append(f"Visual diagrams available for excerpt {idx}")
                    visual_context_used = True

            combined_evidence = "\n\n".join(evidence_text_parts)
            visual_summary_str = "\n".join(visual_summaries) if visual_summaries else "None"

            prompt_text = ITC_SYNTHESIS_PROMPT.format(
                question=question,
                evidence_text=combined_evidence,
                visual_summary=visual_summary_str
            )

            # Note: Visual diagram analysis ([VISUAL DIAGRAM & CHART ANALYSIS]) is already
            # embedded inside combined_evidence from Firestore, while raw PNGs are prefetched
            # asynchronously from GCS for the UI visual evidence cards.
            contents: List[Any] = [prompt_text]

            response = client.models.generate_content(
                model=settings.GENERATION_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=ITC_SYSTEM_PROMPT,
                    temperature=0.2,
                    thinking_config=types.ThinkingConfig(thinking_budget=0)
                )
            )

            raw_answer = response.text.strip() if response.text else ""
            answer_text = strip_source_citations(raw_answer)

            # Check if model judged evidence insufficient internally or declared an out-of-scope refusal
            if "INSUFFICIENT_EVIDENCE:" in answer_text:
                logger.info("Model judged evidence insufficient during synthesis.")
                is_sufficient = False
            elif is_refusal_response(answer_text):
                logger.warning(f"Synthesis resulted in an out-of-scope refusal for query '{question}'. Stripping citations and images.")
                return ChatResponse(
                    answer=answer_text,
                    citations=[],
                    source_type="none",
                    visual_context_used=False,
                    related_images=[],
                    session_id=effective_session_id
                )
            else:
                # Assemble related flowcharts / diagrams from evidence
                related_images = []
                seen_image_keys = set()
                for c in citations:
                    if c.source_type == "document" and c.image_url:
                        key = f"{c.title}:{c.page_number}"
                        if key not in seen_image_keys and (c.has_visual or "presentation" in c.title.lower() or visual_context_used):
                            seen_image_keys.add(key)
                            related_images.append({
                                "image_url": c.image_url,
                                "title": "Official Strategy Architecture & Flowchart" if "presentation" in c.title.lower() else "Official Document Visual Evidence",
                                "document": c.title,
                                "page": c.page_number
                            })

                # If no visual-flagged image yet but document citations exist, attach top matching document pages
                if not related_images:
                    for c in citations:
                        if c.source_type == "document" and c.image_url:
                            key = f"{c.title}:{c.page_number}"
                            if key not in seen_image_keys:
                                seen_image_keys.add(key)
                                related_images.append({
                                    "image_url": c.image_url,
                                    "title": "Official Document Visual Evidence",
                                    "document": c.title,
                                    "page": c.page_number
                                })
                                if len(related_images) >= 2:
                                    break

                chat_resp = ChatResponse(
                    answer=answer_text,
                    citations=citations,
                    source_type="document",
                    visual_context_used=visual_context_used or bool(related_images),
                    related_images=related_images,
                    session_id=effective_session_id
                )
                self.sessions.setdefault(effective_session_id, []).append({
                    "question": question, "answer": answer_text, "citations": citations,
                    "source_type": "document", "visual_context_used": visual_context_used or bool(related_images),
                    "related_images": related_images
                })
                return chat_resp

        # Step 5: Controlled Web Fallback ONLY if the query is verified to be about ITC Limited
        if has_explicit_itc_kw:
            logger.info(f"Local ITC corpus insufficient for ITC query '{question}'. Triggering controlled Web Search Fallback.")
            web_result = self.tools.search_web_if_needed(question)
            web_text = web_result.get("text", "")
            web_citations = web_result.get("citations", [])

            if web_text and "Unable to retrieve" not in web_text:
                synthesis_prompt = ITC_WEB_SYNTHESIS_PROMPT.format(
                    question=question,
                    web_findings=web_text
                )
                response = client.models.generate_content(
                    model=settings.GENERATION_MODEL,
                    contents=synthesis_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=ITC_SYSTEM_PROMPT,
                        temperature=0.2
                    )
                )
                raw_web_answer = response.text.strip() if response.text else web_text
                final_web_answer = strip_source_citations(raw_web_answer)

                if is_refusal_response(final_web_answer):
                    logger.warning(f"Web synthesis resulted in an out-of-scope refusal for query '{question}'.")
                    return ChatResponse(
                        answer=final_web_answer,
                        citations=[],
                        source_type="none",
                        visual_context_used=False,
                        related_images=[],
                        session_id=effective_session_id
                    )

                chat_resp = ChatResponse(
                    answer=final_web_answer,
                    citations=web_citations,
                    source_type="web",
                    visual_context_used=False,
                    session_id=effective_session_id
                )
                self.sessions.setdefault(effective_session_id, []).append({
                    "question": question, "answer": final_web_answer, "citations": web_citations,
                    "source_type": "web", "visual_context_used": False
                })
                return chat_resp

        # Step 6: Off-topic or unanswerable query
        return ChatResponse(
            answer=ITC_OUT_OF_SCOPE_MESSAGE if not has_explicit_itc_kw else (
                "Sufficient reliable information to answer this inquiry could not be found in the official ITC documents."
            ),
            citations=[],
            source_type="none",
            visual_context_used=False,
            session_id=effective_session_id
        )
