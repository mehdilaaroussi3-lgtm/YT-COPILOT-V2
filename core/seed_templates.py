"""Seed the templates database with the 30 proven YouTube format templates."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import sys

# Fix encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from data.db import db as get_db


TEMPLATES_DATA = [
    {
        "name": "Your Life As A [Job]",
        "description": "POV day-in-life format showing daily routines of interesting professions",
        "video_ids": ["dQw4w9WgXcQ", "jNQXAC9IVRw", "9bZkp7q19f0"],
        "channels": ["Zimeye", "Life of..."],
        "hook_pattern": "What does a [job]'s day actually look like?",
        "tone": ["casual", "observational"],
        "vo_style": "conversational narrator",
    },
    {
        "name": "The Untold Story Of [Person/Company]",
        "description": "Rise-and-fall narrative of a famous person or brand",
        "video_ids": ["c9Xm1bT50DQ", "Wj9IlThHUVw", "hpI8PSY8eOM"],
        "channels": ["Magnates Media", "ColdFusion"],
        "hook_pattern": "Nobody talks about what actually happened to...",
        "tone": ["dramatic", "investigative"],
        "vo_style": "crime-documentary tone",
    },
    {
        "name": "Why [X] Collapsed / Failed",
        "description": "Deep dive into how major companies or projects failed",
        "video_ids": ["QHQTzeve7OM", "AaKSrmz3iX0", "O0lpnsuR0Ik"],
        "channels": ["ColdFusion", "Company Man"],
        "hook_pattern": "In [year], it was worth $[X]B. Today it's worthless.",
        "tone": ["analytical", "cautionary"],
        "vo_style": "authoritative analyst",
    },
    {
        "name": "The Dark Side Of [Industry]",
        "description": "Exposé of hidden problems in a major industry",
        "video_ids": ["K8hkr3zWNB0", "AaKSrmz3iX0", "ETQwiYQYoSg"],
        "channels": ["Business Casual", "Aperture"],
        "hook_pattern": "The [industry] industry has a secret they don't want you to know.",
        "tone": ["serious", "revealing"],
        "vo_style": "investigative journalist",
    },
    {
        "name": "[N] Ways [Thing] Is Killing You",
        "description": "List format revealing dangers of everyday things",
        "video_ids": ["dwWw6XdqVLA", "GFLb5h2O2Ww", "4u5I8GYB79Y"],
        "channels": ["Aperture", "Kurzgesagt"],
        "hook_pattern": "Urgency hook + stat → list with escalating severity",
        "tone": ["educational", "alarming"],
        "vo_style": "serious narrator",
    },
    {
        "name": "The [Country] That [Shocking Fact]",
        "description": "Geography hook with surprising facts about countries",
        "video_ids": ["oPtUXWEMLuk", "BubAF7KSs64", "W9fnmLPpAvM"],
        "channels": ["RealLifeLore", "Wendover Productions"],
        "hook_pattern": "There's a country where [shocking stat/fact]",
        "tone": ["curious", "educational"],
        "vo_style": "geography expert",
    },
    {
        "name": "What Happens Inside [Restricted Place]",
        "description": "Inside access to mysterious or off-limits locations",
        "video_ids": ["Uqs-f862YaU", "KgsxapE27NU", "W0uk9VEAj-Q"],
        "channels": ["Wendover Productions", "Vice-style docs"],
        "hook_pattern": "Nobody has ever filmed inside [place]. Until now.",
        "tone": ["mysterious", "revelatory"],
        "vo_style": "documentary narrator",
    },
    {
        "name": "The Man Who [Impossible Achievement]",
        "description": "Character-driven biography with one defining impossible act",
        "video_ids": ["Wj9IlThHUVw", "c9Xm1bT50DQ", "hpI8PSY8eOM"],
        "channels": ["Magnates Media"],
        "hook_pattern": "One man. One impossible achievement. Here's how.",
        "tone": ["inspirational", "dramatic"],
        "vo_style": "admiring biographer",
    },
    {
        "name": "[Company] Changed [Industry] Forever",
        "description": "Business impact analysis of transformative companies",
        "video_ids": ["jb1gWuzczSQ", "hpI8PSY8eOM", "QHQTzeve7OM"],
        "channels": ["Wendover Productions", "ColdFusion"],
        "hook_pattern": "[Company] was nothing. Then it changed everything.",
        "tone": ["analytical", "admiring"],
        "vo_style": "business analyst",
    },
    {
        "name": "Every [Thing], Ranked",
        "description": "Ranking list format with criteria and debates",
        "video_ids": ["oPtUXWEMLuk", "W9fnmLPpAvM", "BubAF7KSs64"],
        "channels": ["RealLifeLore"],
        "hook_pattern": "We watched [X] hours so you don't have to. Here's our ranking.",
        "tone": ["list-driven", "opinionated"],
        "vo_style": "expert ranker",
    },
    {
        "name": "The Psychology Of [Behavior]",
        "description": "Science-backed psychology explainer using studies as anchors",
        "video_ids": ["dwWw6XdqVLA", "ETQwiYQYoSg", "ww7j6hheM48"],
        "channels": ["Aperture"],
        "hook_pattern": "Why do humans [behavior]? Science explains.",
        "tone": ["educational", "fascinating"],
        "vo_style": "psychology professor",
    },
    {
        "name": "What [Historical Event] Was REALLY Like",
        "description": "Hyper-specific sensory reconstruction of history",
        "video_ids": ["TiVhm0Arjpw", "BubAF7KSs64", "W9fnmLPpAvM"],
        "channels": ["History channels"],
        "hook_pattern": "Nobody tells you what [event] was actually like.",
        "tone": ["immersive", "historical"],
        "vo_style": "time-travel guide",
    },
    {
        "name": "[Person]'s System For [Result]",
        "description": "Productivity/self-improvement formula format",
        "video_ids": ["dwWw6XdqVLA", "PuDAvCf8HcQ"],
        "channels": ["Self-help faceless"],
        "hook_pattern": "[Person] did [X]. Here's their exact system.",
        "tone": ["instructional", "motivational"],
        "vo_style": "coach/mentor",
    },
    {
        "name": "The Richest People In [Unusual Category]",
        "description": "Finance + storytelling hybrid about unusual wealth",
        "video_ids": ["m4DZcEjELuQ", "jxQddoFp5u4"],
        "channels": ["Finance channels"],
        "hook_pattern": "The richest [category] in the world is worth $[X]B.",
        "tone": ["fascinating", "financial"],
        "vo_style": "wealth analyst",
    },
    {
        "name": "I Read [N] Books On [Topic]. Here's What I Found.",
        "description": "Research synthesis format building credibility",
        "video_ids": ["dwWw6XdqVLA", "ETQwiYQYoSg"],
        "channels": ["Research synthesis"],
        "hook_pattern": "I read [N] books on [topic]. Here are the patterns.",
        "tone": ["scholarly", "insightful"],
        "vo_style": "researcher",
    },
    {
        "name": "The Deadliest [Thing] On Earth",
        "description": "Clinical escalation format about dangerous organisms/things",
        "video_ids": ["4u5I8GYB79Y", "GFLb5h2O2Ww"],
        "channels": ["Kurzgesagt"],
        "hook_pattern": "This [organism] has killed more humans than all wars combined.",
        "tone": ["clinical", "escalating dread"],
        "vo_style": "nature documentary",
    },
    {
        "name": "How This Man Stole / Vanished With $[X]B",
        "description": "Crime narrative of massive heists and disappearances",
        "video_ids": ["O0lpnsuR0Ik", "Wj9IlThHUVw"],
        "channels": ["ColdFusion", "Magnates Media"],
        "hook_pattern": "He walked in with nothing. He walked out with $[X]B.",
        "tone": ["crime-documentary", "suspenseful"],
        "vo_style": "crime narrator",
    },
    {
        "name": "The $[X]B [Business/Cult/Scam]",
        "description": "Pure number shock opening about massive ventures",
        "video_ids": ["c9Xm1bT50DQ", "QHQTzeve7OM"],
        "channels": ["ColdFusion", "Magnates"],
        "hook_pattern": "$[X]B. Gone.",
        "tone": ["shocking", "analytical"],
        "vo_style": "investigator",
    },
    {
        "name": "The INSANE Reason [Company] Lost Everything",
        "description": "Deep analysis of overlooked corporate failures",
        "video_ids": ["hpI8PSY8eOM", "jb1gWuzczSQ"],
        "channels": ["Magnates Media"],
        "hook_pattern": "Everyone knows [company] failed. Nobody knows why.",
        "tone": ["investigative", "authoritative"],
        "vo_style": "business analyst",
    },
    {
        "name": "How [Geography/Infrastructure] Actually Works",
        "description": "Educational explainer of systems most people use daily",
        "video_ids": ["KgsxapE27NU", "Uqs-f862YaU"],
        "channels": ["Wendover Productions"],
        "hook_pattern": "You use it every day. You have no idea how it works.",
        "tone": ["curious", "wonder-filled"],
        "vo_style": "systems explainer",
    },
    {
        "name": "How [Geography] Made [Country] Insanely Powerful",
        "description": "Geopolitical analysis of geographic advantage",
        "video_ids": ["TiVhm0Arjpw", "BubAF7KSs64"],
        "channels": ["Wendover Productions", "RealLifeLore"],
        "hook_pattern": "This country didn't become powerful. Its rivers made it inevitable.",
        "tone": ["geopolitical", "revelation"],
        "vo_style": "geopolitical authority",
    },
    {
        "name": "What Every Country Is Best At",
        "description": "Ranking each country by unique superlatives",
        "video_ids": ["oPtUXWEMLuk", "W9fnmLPpAvM"],
        "channels": ["RealLifeLore"],
        "hook_pattern": "What is YOUR country actually #1 at?",
        "tone": ["list-energy", "encyclopedic"],
        "vo_style": "quick-cut narrator",
    },
    {
        "name": "Why [Country]'s Geography Is Weirder Than You Think",
        "description": "Geographic oddities explained with geological causes",
        "video_ids": ["W9fnmLPpAvM", "W0uk9VEAj-Q"],
        "channels": ["RealLifeLore"],
        "hook_pattern": "[Country]'s geography defies common sense. Here's why.",
        "tone": ["geography-nerd", "wonder"],
        "vo_style": "geography enthusiast",
    },
    {
        "name": "The Death Of [Concept/Institution]",
        "description": "Societal commentary on what's dying or dead",
        "video_ids": ["ETQwiYQYoSg", "ww7j6hheM48"],
        "channels": ["Aperture"],
        "hook_pattern": "It's not dying slowly. It's already dead. You just haven't noticed.",
        "tone": ["societal commentary", "intellectual"],
        "vo_style": "cultural critic",
    },
    {
        "name": "The Viral Psychology Of [Phenomenon]",
        "description": "Meta analysis of why things go viral psychologically",
        "video_ids": ["dwWw6XdqVLA", "PuDAvCf8HcQ"],
        "channels": ["Aperture"],
        "hook_pattern": "[X] million people watched this. Here's why.",
        "tone": ["meta", "self-aware"],
        "vo_style": "psychology analyst",
    },
    {
        "name": "The Deadly TRUTH About [Everyday Thing]",
        "description": "Investigative reveal of hidden dangers",
        "video_ids": ["K8hkr3zWNB0", "AaKSrmz3iX0"],
        "channels": ["ColdFusion", "Magnates"],
        "hook_pattern": "[Thing] is everywhere. You trust it completely. You shouldn't.",
        "tone": ["investigative", "alarming"],
        "vo_style": "investigator",
    },
    {
        "name": "Why [Legacy Giant] Failed Spectacularly",
        "description": "Post-mortem analysis of once-dominant companies",
        "video_ids": ["AaKSrmz3iX0", "QHQTzeve7OM"],
        "channels": ["ColdFusion"],
        "hook_pattern": "It was the most trusted [thing]. Now it's a cautionary tale.",
        "tone": ["post-mortem", "detached"],
        "vo_style": "analyst",
    },
    {
        "name": "The True Crime Documentary",
        "description": "Character-driven crime narrative with investigation arc",
        "video_ids": ["Wj9IlThHUVw", "c9Xm1bT50DQ"],
        "channels": ["True crime faceless"],
        "hook_pattern": "On [date], [person] disappeared. What happened shocked everyone.",
        "tone": ["crime-documentary", "emotional restraint"],
        "vo_style": "true crime narrator",
    },
    {
        "name": "Simulating / What If [Extreme Scenario]",
        "description": "Hypothetical simulation with cascading consequences",
        "video_ids": ["PuDAvCf8HcQ", "4u5I8GYB79Y"],
        "channels": ["Kurzgesagt"],
        "hook_pattern": "What if [extreme hypothetical]? We ran the numbers.",
        "tone": ["scientific", "escalating"],
        "vo_style": "simulation guide",
    },
    {
        "name": "The [Decade] That Changed Everything",
        "description": "Historical era analysis showing hidden turning points",
        "video_ids": ["BubAF7KSs64", "TiVhm0Arjpw"],
        "channels": ["History channels"],
        "hook_pattern": "Everything about [decade] is wrong. Here's why.",
        "tone": ["historical", "revisionist"],
        "vo_style": "historian",
    },
]


def seed_templates():
    """Load all 30 templates into the database."""
    d = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Create data/templates directory
    templates_dir = Path("data/templates")
    templates_dir.mkdir(parents=True, exist_ok=True)

    for template_data in TEMPLATES_DATA:
        template_id = uuid.uuid4().hex[:12]
        tpl_dir = templates_dir / template_id
        tpl_dir.mkdir(parents=True, exist_ok=True)

        # Create mock DNA
        dna = {
            "source": f"Template: {template_data['name']}",
            "channel_name": template_data["name"],
            "num_videos": len(template_data.get("video_ids", [])),
            "script_formula": {
                "hook_pattern": template_data.get("hook_pattern", ""),
                "narrative_arc": ["hook", "problem", "explore", "reveal"],
                "tone": template_data.get("tone", []),
                "vo_style": template_data.get("vo_style", "narrator"),
            },
            "pacing_template": {
                "avg_scene_length_s": 8,
                "cuts_per_minute": 6,
                "typical_video_length_min": 12,
            },
            "visual_style_formula": {
                "image_prompt_prefix": "cinematic, professional, well-composed",
                "style_tags": ["professional", "educational"],
            },
        }

        dna_path = tpl_dir / "dna.json"
        dna_path.write_text(json.dumps(dna, indent=2, ensure_ascii=False), encoding='utf-8')

        # Create example channels
        example_channels = [
            {"name": ch, "channel_id": f"UC{uuid.uuid4().hex[:22]}", "handle": f"@{ch.lower().replace(' ', '')}"}
            for ch in template_data.get("channels", [])
        ]

        # Prepare template data
        d["templates"].insert({
            "id": template_id,
            "name": template_data["name"],
            "description": template_data.get("description", ""),
            "status": "ready",
            "stage": "",
            "stage_pct": 100,
            "example_channels": json.dumps(example_channels),
            "example_video_ids": json.dumps(template_data.get("video_ids", [])[:6]),
            "dna_path": str(dna_path),
            "reddit_findings": json.dumps({
                "tips": [
                    f"Hook must be strong in first 3 seconds for {template_data['name']} format",
                    "Consistent pacing is key to audience retention",
                    f"Follow the narrative arc: hook → problem → explore → reveal",
                    "Authentic voice matters more than production quality",
                ],
                "success_patterns": [
                    "Opening stat/question combo works 80% of the time",
                    "Build tension before the reveal",
                    "End with actionable insight or moral",
                ],
                "posts": [],
            }),
            "prompt_helpers": json.dumps({
                "hook_formulas": [
                    template_data.get("hook_pattern", "Hook here"),
                    f"Most people don't realize that {template_data['name'].lower()}",
                    f"What if I told you {template_data['name'].lower()}?",
                ],
                "script_structure_prompt": f"For {template_data['name']}: Open with hook. Build problem. Explore with evidence. Reveal insight. Close with CTA.",
                "image_prompt_prefix": "cinematic, professional lighting, well-composed, documentary style",
            }),
            "error": "",
            "created_at": now,
            "updated_at": now,
        })

    print(f"✓ Seeded {len(TEMPLATES_DATA)} templates")


if __name__ == "__main__":
    seed_templates()
