"""Seed the channel registry with ~100 curated top-performing channels across 10 niches.

Call `seed_registry()` once (or with force=True) to resolve all handles via the
YouTube API and write them into channels_registry.yml. After that, the weekly scan
picks them up automatically.

Quota cost: ~1 unit per new handle (channels.list?forHandle=). ~380 units total for
a first run — well within the 10,000/day free quota.
"""
from __future__ import annotations

from typing import Callable

CURATED_CHANNELS: dict[str, list[dict]] = {
    # ── Viral / Mega Creators ────────────────────────────────────────────────
    "viral_entertainment": [
        {"handle": "@MrBeast",           "style_tags": ["big_stunt", "face_shocked", "bright_logo"],         "why": "Largest YouTube channel; every thumbnail is a masterclass"},
        {"handle": "@MarkRober",         "style_tags": ["engineering_stunt", "face_excited", "big_reveal"],  "why": "Science + viral stunts; highest production thumbnails"},
        {"handle": "@Vsauce",            "style_tags": ["curiosity_gap", "minimal_face", "clean"],           "why": "Pioneer of the curious title + minimal thumbnail format"},
        {"handle": "@jacksepticeye",     "style_tags": ["face_reaction", "high_energy", "bright_bg"],        "why": "Classic face+emotion formula; proven CTR machine"},
        {"handle": "@penguinz0",         "style_tags": ["ironic_minimal", "white_bg", "face_deadpan"],       "why": "Ironic minimal; extremely high outlier scores"},
        {"handle": "@Tommyinnit",        "style_tags": ["face_young_viral", "loud_color", "high_energy"],    "why": "Gen-Z viral sensation; chaotic high-energy style"},
        {"handle": "@DanTDM",            "style_tags": ["face_excited_game", "bright", "logo_prominent"],    "why": "Long-running gaming/family huge audience"},
        {"handle": "@YesTheory",         "style_tags": ["adventure_group", "emotional", "outdoor_bright"],   "why": "Challenge + adventure viral lifestyle"},
        {"handle": "@JackFilms",         "style_tags": ["parody_face", "bold_text_humor", "white_clean"],    "why": "Comedy parody; highly distinctive style"},
        {"handle": "@CaseyNeistat",      "style_tags": ["cinematic_vlog", "nyc_aesthetic", "moody"],         "why": "Pioneered cinematic vlog; still highly influential"},
        {"handle": "@PewDiePie",         "style_tags": ["face_bold", "high_saturation", "meme_adjacent"],    "why": "Most subscribed individual creator in history"},
    ],
    # ── Science & Education ──────────────────────────────────────────────────
    "science_education": [
        {"handle": "@Veritasium",        "style_tags": ["curiosity_gap", "science_photo", "clean_face"],     "why": "Top science channel; curiosity-gap master"},
        {"handle": "@3Blue1Brown",       "style_tags": ["math_animation", "clean_3d", "minimal"],            "why": "Math visualization; gold standard educational"},
        {"handle": "@SmarterEveryDay",   "style_tags": ["slow_motion_reveal", "face_curious", "science"],    "why": "Slow-mo science; face-forward experiment style"},
        {"handle": "@MinutePhysics",     "style_tags": ["whiteboard_animation", "fast_explainer", "clean"],  "why": "Rapid physics explainer minimal animation style"},
        {"handle": "@RealEngineering",   "style_tags": ["technical_diagram", "infographic_clean", "pro"],    "why": "Engineering explainer professional diagram style"},
        {"handle": "@Kurzgesagt",        "style_tags": ["2d_illustrated", "bright_palette", "character"],    "why": "Gold standard animated explainer, 20M+ subs"},
        {"handle": "@SciShow",           "style_tags": ["bright_lab", "face_excited", "bold_title"],         "why": "Classic science explainer bright look"},
        {"handle": "@pbsspacetime",      "style_tags": ["deep_space", "minimal_text", "cosmic"],             "why": "Premium physics dark cosmic aesthetic"},
        {"handle": "@AntonPetrov",       "style_tags": ["space_photo", "news_style", "rapid_update"],        "why": "Daily space news photo collage urgency"},
        {"handle": "@ScienceClic",       "style_tags": ["3d_simulation", "clean_motion", "no_face"],         "why": "Stunning 3D simulation thumbnails"},
        {"handle": "@Domain_of_Science", "style_tags": ["mind_map", "colorful_diagram", "educational"],      "why": "Science mind-maps; unique visual style"},
        {"handle": "@ArvinAsh",          "style_tags": ["physics_diagram", "whiteboard", "face_serious"],    "why": "Theoretical physics face+diagram combo"},
        {"handle": "@SabineHossenfelder","style_tags": ["talking_head", "minimal", "direct_expert"],         "why": "Contrarian science; high CTR minimal style"},
        {"handle": "@PracticalEngineeringUS", "style_tags": ["civil_engineering", "model_demo", "clean"],    "why": "Civil engineering demos; very clear thumbnails"},
        {"handle": "@WendoverProductions","style_tags": ["map_diagram", "clean_professional", "aviation"],   "why": "Aviation/logistics with clean map diagram style"},
        {"handle": "@HalfasInteresting", "style_tags": ["quirky_infographic", "pastel_map", "humor"],        "why": "Quirky geography facts; extremely distinctive style"},
        {"handle": "@CGPGrey",           "style_tags": ["minimal_icon", "clean_animation", "faceless"],      "why": "Animation-explainer pioneer; timeless minimalism"},
        {"handle": "@TED-Ed",            "style_tags": ["2d_illustrated", "clean_animation", "educational"], "why": "TED brand authority, consistent format"},
        {"handle": "@RealLifeLore",      "style_tags": ["map_overlay", "infographic", "clean_data"],         "why": "Geography+society infographic style"},
        {"handle": "@Astrum",            "style_tags": ["space_photo", "minimal", "cinematic_planet"],       "why": "Space cinematic minimal style"},
    ],
    # ── History ──────────────────────────────────────────────────────────────
    "history_education": [
        {"handle": "@Oversimplified",    "style_tags": ["2d_illustrated", "humour_visual", "cartoon"],       "why": "Comic-book history, enormous CTR"},
        {"handle": "@KingsandGenerals",  "style_tags": ["map_style", "battle_illustration", "dramatic"],     "why": "Military history map-style thumbnails"},
        {"handle": "@Invicta",           "style_tags": ["ancient_world", "minimal_icon", "gold_palette"],    "why": "Ancient history minimal icon + gold tone"},
        {"handle": "@EpicHistoryTV",     "style_tags": ["cinematic_battle", "dramatic_scale", "editorial"],  "why": "Military history dramatic scale visual"},
        {"handle": "@toldinstone",       "style_tags": ["talking_head", "academic_informal", "chalkboard"],  "why": "Classics prof; face-forward academic look"},
        {"handle": "@FallofCivilizations","style_tags": ["dark_cinematic", "ambient", "minimal_text"],       "why": "Atmospheric long-form docu; very high outlier scores"},
        {"handle": "@HistoryHit",        "style_tags": ["editorial_photo", "documentary_style", "news"],     "why": "Professional documentary channel brand"},
        {"handle": "@HistoryMarche",     "style_tags": ["animated_map", "simple_diagram", "fast"],           "why": "Animated map history; very fast format"},
        {"handle": "@HistoricalBeef",    "style_tags": ["humour_face", "bold_text", "comedy_history"],       "why": "Comedy history mashup style"},
        {"handle": "@RyanChapman",       "style_tags": ["editorial_essay", "book_visual", "face_serious"],   "why": "History essay face+book aesthetic"},
    ],
    # ── True Crime & Documentary ─────────────────────────────────────────────
    "true_crime": [
        {"handle": "@MurderMountain",    "style_tags": ["dark_photo", "cinematic_border", "red_title"],      "why": "Mountain crime dark aesthetic"},
        {"handle": "@BaileySarian",      "style_tags": ["beauty_crime_mashup", "face_glam", "storytelling"], "why": "Beauty + crime unique niche crossover"},
        {"handle": "@StephanieHarlowe",  "style_tags": ["face_forward_close", "warm_grade", "emotional"],    "why": "Intimate face-to-camera storytelling"},
        {"handle": "@KendallRae",        "style_tags": ["face_forward", "warm_bg", "trusting"],              "why": "Female face-forward true crime huge audience"},
        {"handle": "@CriminallyListed",  "style_tags": ["countdown_style", "bold_number", "dark_photo"],     "why": "List-format crime with bold number overlay"},
        {"handle": "@EleanorNeale",      "style_tags": ["face_serious", "dark_editorial", "bold_title"],     "why": "UK true crime face-forward serious tone"},
        {"handle": "@Fern",              "style_tags": ["3d_cinematic", "dark_moody", "minimal_text"],       "why": "3D cinematic true crime visuals"},
        {"handle": "@JCS",              "style_tags": ["interrogation_footage", "minimal", "text_focused"],  "why": "Pioneered the crime breakdown format"},
        {"handle": "@Coffeehousecrime",  "style_tags": ["editorial", "high_contrast", "red_accent"],         "why": "Professional editorial consistent brand"},
        {"handle": "@NightDocumentaries","style_tags": ["dark_night", "cinematic_still", "moody_text"],      "why": "Dark night-time crime aesthetic"},
    ],
    # ── AI & Technology ──────────────────────────────────────────────────────
    "ai_tech": [
        {"handle": "@Fireship",          "style_tags": ["bold_icon", "gradient_bg", "minimal_text"],         "why": "Iconic minimalist thumbnails, instant recognition"},
        {"handle": "@MattWolfe",         "style_tags": ["tech_collage", "blue_palette", "screenshot"],       "why": "AI tool roundup format with high CTR"},
        {"handle": "@AIExplained",       "style_tags": ["clean_diagram", "educational", "minimal"],          "why": "Authoritative AI explainer style"},
        {"handle": "@TheAIGRID",         "style_tags": ["news_style", "bold_text", "dark_neon"],             "why": "News-style AI thumbnails with urgency"},
        {"handle": "@TwoMinutePapers",   "style_tags": ["screenshot_demo", "before_after", "tech_visual"],   "why": "Research visualization paper screenshot style"},
        {"handle": "@Andrej_Karpathy",   "style_tags": ["lecture_style", "whiteboard", "expert_minimal"],    "why": "Deep learning expert; high authority content"},
        {"handle": "@YannicKilcher",     "style_tags": ["paper_visual", "face_serious", "academic"],         "why": "ML paper breakdowns; highly engaged niche audience"},
        {"handle": "@LexFridman",        "style_tags": ["podcast_face_bw", "minimal_clean", "serious_tone"], "why": "AI/tech podcast; top outlier scores on big interviews"},
        {"handle": "@Computerphile",     "style_tags": ["whiteboard_code", "uk_academic", "minimal"],        "why": "Deep computer science topics; cult following"},
        {"handle": "@SebastianLague",    "style_tags": ["code_simulation", "clean_demo", "satisfying"],      "why": "Coding simulations; stunning visual results"},
        {"handle": "@TheEngineeringMindset","style_tags": ["technical_diagram", "professional", "explainer"],"why": "Electrical engineering clean diagram style"},
        {"handle": "@ThePrimeagen",      "style_tags": ["face_reaction_code", "terminal_bg", "dev_culture"], "why": "Developer culture face reaction style"},
        {"handle": "@Theo",              "style_tags": ["dev_face", "hot_take", "bold_claim"],               "why": "Web dev hot takes high CTR face-forward"},
    ],
    # ── Tech Reviews & Gadgets ───────────────────────────────────────────────
    "tech_reviews": [
        {"handle": "@MKBHD",             "style_tags": ["product_minimal", "black_bg", "flagship"],          "why": "Gold standard product review minimal style"},
        {"handle": "@LinusTechTips",     "style_tags": ["face_product_excited", "multi_grid", "bright"],     "why": "High-energy tech review face + product grid"},
        {"handle": "@UnboxTherapy",      "style_tags": ["unbox_reveal", "face_amazed", "dramatic"],          "why": "Unboxing reaction dramatic reveal format"},
        {"handle": "@Dave2D",            "style_tags": ["minimal_flat_lay", "clean_bg", "apple_adjacent"],   "why": "Minimal flat-lay product style"},
        {"handle": "@JerryRigEverything","style_tags": ["teardown_visual", "face_tool", "destruction"],      "why": "Durability test destruction thumbnail proof"},
        {"handle": "@MrMobile",          "style_tags": ["cinematic_tech", "travel_product", "moody"],        "why": "Cinematic mobile review with travel aesthetic"},
        {"handle": "@SnazzyLabs",        "style_tags": ["mac_minimal", "white_clean", "soft_product"],       "why": "macOS/Apple minimal clean white aesthetic"},
        {"handle": "@UrAvgConsumer",     "style_tags": ["face_comparison", "split_layout", "bold_title"],    "why": "Value-focused comparison split-screen layout"},
        {"handle": "@MrWhosTheBoss",     "style_tags": ["face_shocked", "product_reveal", "high_energy"],    "why": "Viral tech reveal face-forward high energy"},
        {"handle": "@GadgetsBoy",        "style_tags": ["clean_product", "white_bg", "studio_shot"],         "why": "Clean studio product shots"},
        {"handle": "@ShortCircuit",      "style_tags": ["unbox_face", "bright_product", "linus_adjacent"],   "why": "LTT secondary; fresh product reaction style"},
        {"handle": "@iJustine",          "style_tags": ["face_product_happy", "bright_color", "approachable"],"why": "Female tech face-forward approachable style"},
    ],
    # ── Finance & Money ──────────────────────────────────────────────────────
    "finance_money": [
        {"handle": "@GrahamStephan",     "style_tags": ["face_forward", "real_estate", "bold_dollar"],       "why": "High-CTR personal finance face-forward"},
        {"handle": "@AndreiJikh",        "style_tags": ["clean_graphic", "stock_visual", "face_confident"],  "why": "Investing clean polished graphic style"},
        {"handle": "@HumphreyYang",      "style_tags": ["finance_explainer", "clean", "approachable_face"],  "why": "Personal finance explainer relatable face"},
        {"handle": "@MinorityMindset",   "style_tags": ["bold_text", "face_forward", "finance_urgency"],     "why": "Financial freedom urgency bold text style"},
        {"handle": "@HowMoneyWorks",     "style_tags": ["infographic", "bold_numbers", "green_clean"],       "why": "1M+ subs faceless, infographic-style thumbnails"},
        {"handle": "@EconomicsExplained","style_tags": ["diagram", "editorial", "data_viz", "clean_pro"],    "why": "Professional explainer with data visuals"},
        {"handle": "@PatrickBoyle",      "style_tags": ["editorial", "newspaper_style", "sophisticated"],    "why": "Sophisticated finance editorial look"},
        {"handle": "@MoneyandMacro",     "style_tags": ["data_chart", "clean", "professional", "blue"],      "why": "Macro economics data chart style"},
        {"handle": "@PlainBagel",        "style_tags": ["clean_minimal", "face_neutral", "finance_safe"],    "why": "Calm finance explainer clean minimal face"},
        {"handle": "@TwoFourProductions","style_tags": ["business_news", "bold_graphic", "editorial"],       "why": "Finance news bold editorial style"},
        {"handle": "@Coffeezilla",       "style_tags": ["bold_expose", "red_accent", "dark_face"],           "why": "Exposé journalist style, extremely high CTR"},
        {"handle": "@NateOBrien",        "style_tags": ["clean_pastel", "face_relaxed", "minimalist"],       "why": "Millennial minimalist finance lifestyle"},
        {"handle": "@JosephCarlsonAfterHours","style_tags": ["portfolio_visual", "face_chart", "investing"], "why": "Dividend investing face + portfolio chart"},
    ],
    # ── Business & Entrepreneur ──────────────────────────────────────────────
    "business_entrepreneur": [
        {"handle": "@AliAbdaal",         "style_tags": ["clean_minimal", "face_side", "productivity"],       "why": "Productivity/entrepreneur clean pastel look"},
        {"handle": "@ColinandSamir",     "style_tags": ["creator_economy", "talking_head", "warm_tone"],     "why": "Creator economy reporting editorial feel"},
        {"handle": "@hbomberguy",        "style_tags": ["essay_style", "bold_red_banner", "face_forward"],   "why": "Long-form exposé; extremely high outlier scores"},
        {"handle": "@ThinkMedia",        "style_tags": ["camera_gear", "clean_bg", "youtube_growth"],        "why": "YouTube/tech business growth style"},
        {"handle": "@DanKoe",            "style_tags": ["minimal_dark", "philosophical_text", "solo_face"],  "why": "Solopreneur aesthetic text-heavy minimal"},
        {"handle": "@ImanGadzhi",        "style_tags": ["dark_luxury", "face_close", "aspirational"],        "why": "Agency/business dark luxe aesthetic"},
        {"handle": "@MyFirstMillion",    "style_tags": ["podcast_bold", "face_two_host", "orange_brand"],    "why": "Podcast business ideas; bold brand style"},
        {"handle": "@ycombinator",       "style_tags": ["startup_talk", "face_founder", "clean_minimal"],    "why": "Startup world deep insights; niche authority"},
        {"handle": "@IndigoVictor",      "style_tags": ["business_case", "bold_graphic", "editorial"],       "why": "Business case study editorial clean style"},
        {"handle": "@PowerfulJRE",       "style_tags": ["podcast_face", "minimal_studio", "white_bg"],       "why": "Joe Rogan; massive outlier base from guests"},
    ],
    # ── Psychology & Self-Help ───────────────────────────────────────────────
    "psychology_self_help": [
        {"handle": "@Charismaoncommand", "style_tags": ["face_double", "warm_grade", "social_proof"],        "why": "Social/charisma split-screen face format"},
        {"handle": "@ImprovementPill",   "style_tags": ["2d_illustrated", "clean_minimal", "metaphor"],      "why": "Animated psychology explainer style"},
        {"handle": "@HealthyGamerGG",    "style_tags": ["face_gaming", "mental_health", "warm_overlay"],     "why": "Gaming meets psychology crossover"},
        {"handle": "@WhatIveLearned",    "style_tags": ["infographic_bold", "faceless_diagram", "neon"],     "why": "Faceless health/psych data-forward style"},
        {"handle": "@BetterIdeas",       "style_tags": ["essay_face", "book_visual", "philosophical_clean"], "why": "Self-improvement philosophy essay style"},
        {"handle": "@Einzelganger",      "style_tags": ["stoic_art", "classical_painting", "minimal_text"],  "why": "Philosophy/stoicism with classical art overlays"},
        {"handle": "@Psych2Go",          "style_tags": ["2d_illustrated", "pastel_palette", "face_icon"],    "why": "Animated psychology tips; massive audience"},
        {"handle": "@AnthonyOblander",   "style_tags": ["face_direct", "bold_claim", "motivational"],        "why": "Direct motivation face with bold claim text"},
        {"handle": "@PursuitofWonder",   "style_tags": ["minimal_dark", "philosophical", "text_art"],        "why": "Minimalist philosophical aesthetic"},
        {"handle": "@Einzelganger",      "style_tags": ["stoic_visual", "classical_art", "minimal"],         "why": "Stoic philosophy classical art thumbnails"},
    ],
    # ── Health & Fitness ────────────────────────────────────────────────────
    "health_fitness": [
        {"handle": "@JeffNippard",       "style_tags": ["scientific_fitness", "face_serious", "data"],       "why": "Science-based lifting face + chart overlay"},
        {"handle": "@AthleanX",          "style_tags": ["face_bold_claim", "body_visual", "text_heavy"],     "why": "Fitness claims dramatic face + body proof"},
        {"handle": "@PictureFit",        "style_tags": ["2d_illustrated_body", "clean", "soft_palette"],     "why": "Animated fitness explainer with body diagrams"},
        {"handle": "@ThomasDeLauer",     "style_tags": ["face_clean_bg", "food_visual", "bold_claim"],       "why": "Keto/fasting face-forward style"},
        {"handle": "@JeremyEthier",      "style_tags": ["face_before_after", "clean_gym", "science"],        "why": "Evidence-based fitness before/after style"},
        {"handle": "@HubermanLab",       "style_tags": ["podcast_face_serious", "neuroscience", "clean"],    "why": "Top health podcast; high retention loyal audience"},
        {"handle": "@DrEricBergDC",      "style_tags": ["face_explain", "health_claim", "bold_text"],        "why": "Health education large audience face-forward"},
        {"handle": "@MikeMutzel",        "style_tags": ["academic_face", "clean_science", "chart"],          "why": "Metabolic health academic style"},
        {"handle": "@NutritionMadeSimple","style_tags": ["infographic_clean", "faceless", "green"],          "why": "Nutrition faceless infographic clean data"},
        {"handle": "@PeterAttiaMD",      "style_tags": ["medical_podcast", "face_serious", "clean"],         "why": "Longevity medicine; highly engaged audience"},
        {"handle": "@AndrewHuberman",    "style_tags": ["lecture_serious", "clean_bg", "expert"],            "why": "Neuroscience education; massive CTR"},
    ],
    # ── Food & Cooking ──────────────────────────────────────────────────────
    "food_cooking": [
        {"handle": "@JoshuaWeissman",    "style_tags": ["food_stunt", "face_taste", "bold_title"],           "why": "High-energy food recreation; massive CTR"},
        {"handle": "@BabbishCulinaryUniverse","style_tags": ["clean_studio_food", "minimal_bg", "recipe"],  "why": "Binging with Babish; clean studio aesthetic"},
        {"handle": "@EthanChlebowski",   "style_tags": ["science_food", "clean_data", "face_neutral"],       "why": "Science-based cooking with clean data style"},
        {"handle": "@AdamRagusea",       "style_tags": ["home_kitchen", "face_explain", "casual"],           "why": "Home cook science; relatable casual style"},
        {"handle": "@SortedFood",        "style_tags": ["uk_food_group", "bright_studio", "challenge"],      "why": "UK food challenge bright studio group style"},
        {"handle": "@Internet_Shaquille","style_tags": ["minimal_food", "dry_humor", "clean"],              "why": "Dry humor food reviews minimal style"},
        {"handle": "@Kenji",             "style_tags": ["serious_cook", "close_food", "technical"],          "why": "J. Kenji Lopez-Alt; technical food science"},
        {"handle": "@FitGreedyMakers",   "style_tags": ["healthy_food_art", "colorful", "macro_shot"],       "why": "Healthy food macro photography style"},
        {"handle": "@ChefJohnFoodWishes","style_tags": ["close_food", "recipe_title", "warm_grade"],         "why": "Classic recipe format; decades of CTR data"},
        {"handle": "@TasteShow",         "style_tags": ["satisfying_cook", "asmr_adjacent", "close_macro"],  "why": "Satisfying cooking process; high retention"},
    ],
    # ── DIY / Maker / Engineering ───────────────────────────────────────────
    "diy_maker": [
        {"handle": "@MichaelReeves",     "style_tags": ["chaotic_maker", "face_manic", "tech_humor"],        "why": "Chaotic engineering humor; extremely high CTR"},
        {"handle": "@WilliamOsman",      "style_tags": ["engineering_comedy", "face_dumb_idea", "bright"],   "why": "Comedy maker; dumb ideas with high production"},
        {"handle": "@SimoneGiertz",      "style_tags": ["bad_robot", "face_smile", "shitty_machines"],       "why": "Queen of Shitty Robots; unique humor style"},
        {"handle": "@StuffMadeHere",     "style_tags": ["engineering_reveal", "face_serious_project", "dark"],"why": "Over-engineered projects; very high outlier scores"},
        {"handle": "@NileRed",           "style_tags": ["chemistry_visual", "color_reaction", "minimal"],    "why": "Chemistry experiments visually stunning style"},
        {"handle": "@NightHawkInLight",  "style_tags": ["science_macro", "glowing", "satisfying"],           "why": "Science macro photography; incredibly satisfying"},
        {"handle": "@RealSurvivorMan",   "style_tags": ["outdoor_survival", "face_challenge", "rugged"],     "why": "Survival skills rugged outdoor thumbnail style"},
        {"handle": "@PracticalEngineeringUS","style_tags": ["infrastructure", "model_demo", "educational"],  "why": "Civil engineering very clear demonstrations"},
        {"handle": "@AvE",               "style_tags": ["workshop_teardown", "face_gruff", "canadian"],      "why": "Tool teardowns; cult engineering following"},
        {"handle": "@Electroboom",       "style_tags": ["shock_humor", "electricity_visual", "face_pain"],   "why": "Electrical engineering humor; huge outlier scores"},
    ],
    # ── Cars & Automotive ───────────────────────────────────────────────────
    "cars_automotive": [
        {"handle": "@DonutMedia",        "style_tags": ["car_reveal", "bold_text", "bright_garage"],         "why": "Highest CTR automotive channel; bold text style"},
        {"handle": "@EngineeringExplained","style_tags": ["whiteboard_car", "face_explain", "technical"],    "why": "Car engineering explanations whiteboard face"},
        {"handle": "@Hoonigan",          "style_tags": ["burnout_action", "bold_brand", "high_energy"],      "why": "Car culture action-forward high energy brand"},
        {"handle": "@RegularCars",       "style_tags": ["car_review_quirky", "face_subtle", "dry_humor"],    "why": "Quirky car reviews; highly distinctive voice"},
        {"handle": "@TitaniumDave",      "style_tags": ["car_deal_hunting", "face_excited", "value"],        "why": "Car buying deals face excited value style"},
        {"handle": "@CarThrottle",       "style_tags": ["uk_car_culture", "group_face", "fun_driving"],      "why": "UK car culture group fun driving style"},
        {"handle": "@Throttle",          "style_tags": ["car_lifestyle", "face_driving", "bold"],            "why": "Car lifestyle driving bold style"},
        {"handle": "@TheSmokingTire",    "style_tags": ["car_review", "face_driving", "road_test"],          "why": "In-depth car reviews road test style"},
        {"handle": "@ExoticCars",        "style_tags": ["supercar_visual", "luxury", "dramatic"],            "why": "Exotic car content luxury dramatic style"},
    ],
    # ── Gaming ───────────────────────────────────────────────────────────────
    "gaming": [
        {"handle": "@videogamedunkey",   "style_tags": ["screenshot_game", "bold_overlay", "humor"],         "why": "Comedy gaming screenshot-heavy style"},
        {"handle": "@Ludwig",            "style_tags": ["face_extreme_reaction", "bold_saturation", "viral"],"why": "Streaming personality viral reaction style"},
        {"handle": "@NakeyJakey",        "style_tags": ["essay_style", "comedic_face", "bold_text"],         "why": "Gaming essay comedy talking head style"},
        {"handle": "@GamersNexus",       "style_tags": ["tech_hardware", "teardown", "professional"],        "why": "PC hardware technical clean style"},
        {"handle": "@SkillUpGaming",     "style_tags": ["review_thumbnail", "face_game_split", "clean"],     "why": "Review-format game+face split layout"},
        {"handle": "@DidYouKnowGaming",  "style_tags": ["retro_screenshot", "bold_logo", "nostalgia"],       "why": "Gaming trivia; bold logo retro screenshot"},
        {"handle": "@SodaPoppin",        "style_tags": ["face_reaction_stream", "colorful", "live"],         "why": "Streaming face reaction high energy"},
        {"handle": "@MoistCr1TiKaL",    "style_tags": ["minimal_face", "dry_humor", "white_bg"],            "why": "Ironic minimal face; huge outlier scorer"},
        {"handle": "@LowSpecGamer",      "style_tags": ["pc_optimization", "face_test", "technical"],        "why": "Budget PC gaming niche; high engagement"},
        {"handle": "@rtgamecrowd",       "style_tags": ["face_challenge", "game_screenshot", "uk_gaming"],   "why": "UK gaming challenges face+screenshot"},
        {"handle": "@Noclip",            "style_tags": ["documentary_game", "cinematic", "no_face"],         "why": "Game documentary cinematic minimal style"},
    ],
    # ── Film & Media Essays ──────────────────────────────────────────────────
    "film_media_essay": [
        {"handle": "@LessonsFromScreenplay","style_tags": ["film_still", "cinematic_essay", "minimal"],      "why": "Film essay minimal; very high retention"},
        {"handle": "@NerdWriter1",       "style_tags": ["film_still", "essay_overlay", "thoughtful"],        "why": "Pop-culture essay thoughtful minimal aesthetic"},
        {"handle": "@EveryFrameaPainting","style_tags": ["film_still", "montage", "cinematic_minimal"],      "why": "Seminal film essay channel; top outlier scores"},
        {"handle": "@Folding_Ideas",     "style_tags": ["essay_face", "dark_bg", "analytical"],              "why": "Long-form analytical essays; viral hit thumbnails"},
        {"handle": "@PenguinzO",         "style_tags": ["ironic_minimal", "reaction", "white_bg"],           "why": "Cross-niche; Charlie reaction to media"},
        {"handle": "@KaptainKristian",   "style_tags": ["branding_essay", "clean_design", "minimal"],        "why": "Brand/design essay clean minimal style"},
        {"handle": "@PolyphonyMusic",    "style_tags": ["music_essay", "score_visual", "minimal"],           "why": "Music theory essay visual clean style"},
        {"handle": "@SchaffrillasProductions","style_tags": ["disney_essay", "colorful_still", "humor"],     "why": "Disney/animation essays colorful still"},
        {"handle": "@ThoughtMaybe",      "style_tags": ["essay_face", "minimal_dark", "critical"],           "why": "Critical media essays minimal dark aesthetic"},
    ],
    # ── Geopolitics & News ───────────────────────────────────────────────────
    "geopolitics_news": [
        {"handle": "@CaspianReport",     "style_tags": ["map_geopolitics", "minimal_clean", "flag"],         "why": "Geopolitics with clean map thumbnails"},
        {"handle": "@TLDRNews",          "style_tags": ["animated_flag", "clean_map", "infographic"],        "why": "Daily geopolitics clean animated map style"},
        {"handle": "@ContraPoints",      "style_tags": ["theatrical_face", "cinematic_art", "provocative"],  "why": "Distinctive theatrical video essay style"},
        {"handle": "@PolyMatter",        "style_tags": ["clean_minimal", "flag_icon", "geopolitics"],        "why": "Geopolitics minimal icon style"},
        {"handle": "@JohnnyHarris",      "style_tags": ["map_overlay", "journalistic", "editorial_photo"],   "why": "Journalism meets travel; top outlier scores"},
        {"handle": "@Vox",               "style_tags": ["motion_graphic", "clean_diagram", "editorial"],     "why": "News explainer polished motion graphic style"},
        {"handle": "@SecondThought",     "style_tags": ["essay_minimal", "face_forward", "political"],       "why": "Political essay minimal face forward style"},
        {"handle": "@RealLifeLore",      "style_tags": ["map_overlay", "infographic", "society_data"],       "why": "Geography/society infographic crossover"},
        {"handle": "@EmperorTigerstar",  "style_tags": ["animated_map", "war_history", "clean_simple"],      "why": "Animated map history wars clean simple"},
        {"handle": "@KnowledgeHusk",     "style_tags": ["explainer_minimal", "dark_aesthetic", "bold"],      "why": "Political/social explainer dark minimal"},
    ],
    # ── Motivation & Lifestyle ───────────────────────────────────────────────
    "motivation_lifestyle": [
        {"handle": "@MattDAvella",       "style_tags": ["minimal_cinematic", "b_roll_face", "soft_grade"],   "why": "Minimalism lifestyle; stunning cinematic style"},
        {"handle": "@NathanielDrew",     "style_tags": ["minimal_travel", "clean_lifestyle", "aesthetic"],   "why": "Aesthetic minimalist lifestyle travel"},
        {"handle": "@PeterMcKinnon",     "style_tags": ["cinematic_photo", "dark_grade", "creative"],        "why": "Photography/videography cinematic dark aesthetic"},
        {"handle": "@BretMaverick",      "style_tags": ["face_motivational", "dark_bg", "bold_title"],       "why": "Motivational content bold dark aesthetic"},
        {"handle": "@MarkManson",        "style_tags": ["bold_text_face", "lifestyle_photo", "confident"],   "why": "Self-help author face + bold text formula"},
        {"handle": "@KyleTegartCreator","style_tags": ["productivity_desk", "minimal_clean", "creator"],     "why": "Creator productivity clean desk style"},
        {"handle": "@FromHere2019",      "style_tags": ["van_life", "travel_minimal", "outdoor"],            "why": "Van life travel minimal outdoor aesthetic"},
        {"handle": "@ElieTahari",        "style_tags": ["fashion_lifestyle", "luxury_minimal", "clean"],     "why": "Luxury fashion minimal clean aesthetic"},
        {"handle": "@PickUpLimes",       "style_tags": ["plant_based", "food_lifestyle", "clean_pastel"],    "why": "Plant-based lifestyle clean pastel aesthetic"},
    ],
    # ── Travel & Adventure ───────────────────────────────────────────────────
    "travel_adventure": [
        {"handle": "@KaraandNate",       "style_tags": ["travel_couple", "adventure_bright", "world_map"],   "why": "Full-time travel couple; consistent CTR"},
        {"handle": "@GabeAndMatt",       "style_tags": ["budget_travel", "face_adventure", "map_overlay"],   "why": "Budget adventure travel high energy"},
        {"handle": "@MarkWiens",         "style_tags": ["food_travel", "face_taste_joy", "local_food"],      "why": "Food travel face-forward joy expression"},
        {"handle": "@ExpeditionSA",      "style_tags": ["overlanding", "4x4_adventure", "remote"],           "why": "Overlanding expedition remote adventure style"},
        {"handle": "@FunForLouis",       "style_tags": ["vlog_adventure", "face_outdoor", "spontaneous"],    "why": "Adventure vlog spontaneous outdoor style"},
        {"handle": "@BaldandBankrupt",   "style_tags": ["dark_travel", "ex_soviet", "face_local"],           "why": "Dark travel ex-Soviet face-local style; huge outlier"},
        {"handle": "@DrewBinsky",        "style_tags": ["face_excited_travel", "bold_fact", "world"],        "why": "Travel facts bold text face excited world map"},
        {"handle": "@KylieAndNorman",    "style_tags": ["couple_travel", "adventure_clean", "world"],        "why": "Travel couple clean adventure world style"},
    ],
    # ── Photography & Filmmaking ─────────────────────────────────────────────
    "photography_filmmaking": [
        {"handle": "@PeterMcKinnon",     "style_tags": ["cinematic_dark", "face_serious", "creator"],        "why": "Top photography/filmmaking educator on YouTube"},
        {"handle": "@Sean_Tucker",       "style_tags": ["philosophical_photo", "face_serious", "minimal"],   "why": "Philosophy of photography minimal face style"},
        {"handle": "@GordonLaing",       "style_tags": ["camera_review_clean", "white_bg", "tech"],          "why": "Camera reviews clean white background style"},
        {"handle": "@TonyAndChelsea",    "style_tags": ["couple_photo", "face_reaction", "camera"],          "why": "Photography couple review format"},
        {"handle": "@DSLRguide",         "style_tags": ["tutorial_clean", "camera_visual", "minimal"],       "why": "Photography tutorial clean minimal style"},
        {"handle": "@KaiW",              "style_tags": ["comedy_camera", "face_uk", "review_humor"],         "why": "Comedy camera reviews UK style"},
        {"handle": "@PolyMike",          "style_tags": ["cinematic_bts", "film_making", "dark"],             "why": "Filmmaking behind-the-scenes dark cinematic"},
        {"handle": "@SylvainGabrielleBurke","style_tags": ["portrait_photo", "face_art", "gallery_aesthetic"],"why": "Portrait photography artistic gallery style"},
    ],
    # ── Music ────────────────────────────────────────────────────────────────
    "music": [
        {"handle": "@RickBeato",         "style_tags": ["music_theory_face", "guitar_visual", "serious"],    "why": "Music theory; extremely high outlier scores"},
        {"handle": "@AdamNeely",         "style_tags": ["music_essay", "bass_visual", "thoughtful"],         "why": "Music theory essays thoughtful face style"},
        {"handle": "@12ToneMusic",       "style_tags": ["music_diagram", "staff_notation", "clean"],         "why": "Music analysis notation clean diagram style"},
        {"handle": "@DavidBennettPiano", "style_tags": ["piano_close", "harmony_visual", "gentle"],          "why": "Piano analysis gentle close-up face style"},
        {"handle": "@SethEverettMusic",  "style_tags": ["music_production", "face_excited", "DAW"],          "why": "Music production excitement face DAW visual"},
        {"handle": "@AudioUniversityYT", "style_tags": ["audio_tech", "clean_diagram", "professional"],      "why": "Audio engineering clean professional diagram"},
        {"handle": "@InsideTheMix",      "style_tags": ["mixing_tutorial", "DAW_screenshot", "professional"],"why": "Mixing tutorials DAW screenshot professional"},
        {"handle": "@Polyphia",          "style_tags": ["guitar_performance", "dark_cinematic", "brand"],    "why": "Guitar band cinematic dark performance style"},
    ],
    # ── Space & Astronomy ────────────────────────────────────────────────────
    "space_astronomy": [
        {"handle": "@ScottManley",       "style_tags": ["space_news", "simulation_visual", "face_expert"],   "why": "Space news daily updates simulation style"},
        {"handle": "@ElonMusk_SpaceX",   "style_tags": ["rocket_launch", "dramatic", "engineering"],         "why": "SpaceX official; launch footage dramatically"},
        {"handle": "@EverydayAstronaut", "style_tags": ["face_excited_launch", "rocket_visual", "bright"],   "why": "Rocket launches face excited bright style"},
        {"handle": "@NASASpaceflight",   "style_tags": ["live_launch", "technical", "engineering_visual"],   "why": "SpaceX/NASA technical launch coverage"},
        {"handle": "@pbsspacetime",      "style_tags": ["deep_space", "physics_visual", "cosmic"],           "why": "Premium physics cosmic aesthetic"},
        {"handle": "@FragmentedSpace",   "style_tags": ["space_cinematic", "dark_ambient", "minimal"],       "why": "Space cinematic dark ambient minimal style"},
        {"handle": "@SciShow_Space",     "style_tags": ["space_bright", "face_excited", "educational"],      "why": "Space education bright face excited"},
    ],
    # ── Comedy & Sketch ──────────────────────────────────────────────────────
    "comedy_sketch": [
        {"handle": "@InternetHistorian", "style_tags": ["dark_humor", "image_collage", "no_face"],           "why": "Dark internet history; extremely high outlier scores"},
        {"handle": "@CasuallyExplained", "style_tags": ["stick_figure_irony", "minimal_humor", "clean"],     "why": "Stick figure ironic explainer; iconic minimal style"},
        {"handle": "@CollegeHumor",      "style_tags": ["sketch_bold", "face_reaction", "bright"],           "why": "Sketch comedy bold face reaction style"},
        {"handle": "@RyanGeorge",        "style_tags": ["pitch_meeting", "face_only", "white_bg"],           "why": "Pitch Meeting format iconic face-only style"},
        {"handle": "@OverlySarcasticProductions","style_tags": ["illustrated_humor", "colorful", "cartoon"], "why": "Illustrated humor colorful cartoon style"},
        {"handle": "@Jazza",             "style_tags": ["art_comedy", "face_excited", "bright_art"],         "why": "Art challenge comedy face excited bright"},
        {"handle": "@SamONellaAcademy",  "style_tags": ["crude_stick_figure", "dark_humor", "minimal"],      "why": "Crude animation dark humor; very distinctive"},
        {"handle": "@JaidenAnimations",  "style_tags": ["personal_animation", "face_illustrated", "relatable"],"why": "Relatable animated stories large audience"},
        {"handle": "@TheOdd1sOut",       "style_tags": ["personal_comic", "illustrated_life", "bright"],     "why": "Personal life illustrated comic style"},
    ],
    # ── Nature & Wildlife ────────────────────────────────────────────────────
    "nature_wildlife": [
        {"handle": "@Kurzgesagt",        "style_tags": ["nature_illustrated", "bright", "ecosystem"],        "why": "Nature explainer illustrated bright"},
        {"handle": "@ClintsTerrorisms",  "style_tags": ["snake_handling", "face_calm", "reptile"],           "why": "Reptile handling calm face close-up"},
        {"handle": "@AntsCanada",        "style_tags": ["ant_colony", "macro_shot", "dark_bg"],              "why": "Ant colony macro photography dark background"},
        {"handle": "@SmithersonianChannel","style_tags": ["wildlife_cinematic", "dramatic", "nature"],       "why": "Premium wildlife cinematic dramatic style"},
        {"handle": "@WhatIveLearned",    "style_tags": ["nature_data", "infographic", "health"],             "why": "Crossover nature/health data style"},
        {"handle": "@ZoosAndAquariums",  "style_tags": ["animal_close", "colorful", "face_animal"],         "why": "Zoo animal close-up colorful style"},
        {"handle": "@EmmaStevenson",     "style_tags": ["wildlife_photography", "clean", "nature"],          "why": "Wildlife photography clean minimal style"},
    ],
    # ── Fashion & Style ──────────────────────────────────────────────────────
    "fashion_style": [
        {"handle": "@GQ",                "style_tags": ["fashion_editorial", "magazine_style", "clean"],     "why": "GQ editorial fashion magazine clean style"},
        {"handle": "@WillysCollection",  "style_tags": ["thrift_fashion", "face_enthusiastic", "bright"],    "why": "Thrift fashion haul bright enthusiastic style"},
        {"handle": "@TeYoung",           "style_tags": ["styling_minimal", "clean_lookbook", "aesthetic"],   "why": "Minimal styling clean lookbook aesthetic"},
        {"handle": "@StyleOnABudget",    "style_tags": ["budget_fashion", "face_outfit", "before_after"],    "why": "Budget fashion before/after face outfit"},
        {"handle": "@AGuyWhoKnows",      "style_tags": ["menswear_minimal", "clean_bg", "product_close"],    "why": "Menswear minimal clean background style"},
        {"handle": "@JessicaHayden",     "style_tags": ["aesthetic_fashion", "clean", "soft_palette"],       "why": "Aesthetic fashion clean soft palette"},
    ],
    # ── Animation ────────────────────────────────────────────────────────────
    "animation": [
        {"handle": "@Kurzgesagt",        "style_tags": ["2d_illustration", "bright_palette", "character"],   "why": "Gold standard animation explainer 20M+ subs"},
        {"handle": "@TED-Ed",            "style_tags": ["2d_illustrated", "educational", "clean"],           "why": "TED animation education consistent format"},
        {"handle": "@Oversimplified",    "style_tags": ["2d_cartoon", "humor", "history"],                   "why": "Comic-book animation history enormous CTR"},
        {"handle": "@TerminalMontage",   "style_tags": ["fast_animation", "meme_visual", "game_parody"],     "why": "Fast animation meme parody viral style"},
        {"handle": "@Jaiden_Animations", "style_tags": ["personal_story", "cute_illustrated", "relatable"],  "why": "Relatable personal story illustrated style"},
        {"handle": "@Rebeltaxi",         "style_tags": ["animation_review", "face_reaction", "cartoon"],     "why": "Animation review face reaction cartoon style"},
        {"handle": "@Gillion",           "style_tags": ["anime_essay", "dark_bg", "minimal_text"],           "why": "Anime essay dark minimal text style"},
    ],
    # ── Crypto & Web3 ────────────────────────────────────────────────────────
    "crypto_web3": [
        {"handle": "@CoinBureau",        "style_tags": ["face_explain", "crypto_visual", "bold"],            "why": "Top crypto channel; professional editorial style"},
        {"handle": "@BitcoinBen",        "style_tags": ["bitcoin_orange", "face_forward", "bold"],           "why": "Bitcoin maximalist bold orange brand"},
        {"handle": "@WhiteBoardCrypto",  "style_tags": ["whiteboard_explainer", "clean_diagram", "minimal"], "why": "Crypto whiteboard explainer clean minimal"},
        {"handle": "@InvestAnswers",     "style_tags": ["data_visual", "face_analyze", "clean"],             "why": "Crypto data analysis clean visual face"},
        {"handle": "@CryptoCapital",     "style_tags": ["price_chart", "bold_text", "urgency"],              "why": "Crypto price chart bold text urgency style"},
    ],
    # ── Language & Culture ───────────────────────────────────────────────────
    "language_culture": [
        {"handle": "@Langfocus",         "style_tags": ["language_map", "clean_educational", "minimal"],     "why": "Language analysis clean map minimal style"},
        {"handle": "@PolyglotPal",       "style_tags": ["face_language", "flag_bg", "enthusiastic"],         "why": "Polyglot face forward flag background style"},
        {"handle": "@NotJustBikes",      "style_tags": ["urban_planning", "map_overlay", "clean"],           "why": "Urban planning map overlay clean style"},
        {"handle": "@Verybecky",         "style_tags": ["cultural_explainer", "face_curious", "minimal"],    "why": "Cultural explainer face minimal style"},
        {"handle": "@LangfocusChanl",    "style_tags": ["linguistic_diagram", "clean", "map"],               "why": "Linguistics diagram clean map style"},
    ],
    # ── Productivity & Dev ───────────────────────────────────────────────────
    "productivity_dev": [
        {"handle": "@AliAbdaal",         "style_tags": ["clean_minimal", "face_side", "productivity"],       "why": "Top productivity channel clean pastel style"},
        {"handle": "@ThomasFrankExplains","style_tags": ["face_organized", "clean_bg", "productivity_tips"], "why": "Productivity tips clean organized face style"},
        {"handle": "@KallawayYT",        "style_tags": ["minimal_workspace", "aesthetic_setup", "clean"],    "why": "Workspace setup aesthetic minimal clean"},
        {"handle": "@NetworkChuck",      "style_tags": ["face_excited_code", "terminal_bg", "hacking"],      "why": "Networking/hacking face excited terminal style"},
        {"handle": "@TechWithTim",       "style_tags": ["coding_tutorial", "face_explain", "clean"],         "why": "Python tutorials clean face explain style"},
        {"handle": "@Fireship",          "style_tags": ["bold_code_icon", "gradient", "minimal"],            "why": "Dev content iconic minimalist thumbnails"},
        {"handle": "@Coderized",         "style_tags": ["code_explainer", "minimal_terminal", "clean"],      "why": "Programming explainer minimal terminal clean"},
    ],
    # ── Long-form Documentary ────────────────────────────────────────────────
    "documentary_essay": [
        {"handle": "@RealEngineering",   "style_tags": ["infographic", "technical", "professional"],         "why": "Long-form engineering docs; top outlier scorer"},
        {"handle": "@ColdFusion",        "style_tags": ["tech_history", "dark_minimal", "face_narrate"],     "why": "Tech history dark minimal narration style"},
        {"handle": "@NELAntarctica",     "style_tags": ["exploration_cinematic", "dark", "remote"],          "why": "Extreme exploration cinematic dark style"},
        {"handle": "@FallofCivilizations","style_tags": ["dark_cinematic", "ambient", "minimal_text"],       "why": "History documentary atmospheric style"},
        {"handle": "@WendoverProductions","style_tags": ["map_diagram", "aviation", "logistics"],            "why": "Logistics/aviation diagram map style"},
        {"handle": "@CriticalDrinker",   "style_tags": ["film_review_face", "whisky", "critical"],           "why": "Film criticism Scottish face whisky style"},
        {"handle": "@PatrickHWilliamson","style_tags": ["geopolitics_doc", "face_serious", "map"],           "why": "Geopolitics documentary face serious map"},
        {"handle": "@Whittleblox",       "style_tags": ["craft_doc", "hand_made", "warm_grade"],             "why": "Craft documentary warm grade hand-made"},
        {"handle": "@JMK",               "style_tags": ["economics_doc", "clean_visual", "data"],            "why": "Economics documentary clean visual data"},
    ],
    # ── Sneaker & Streetwear ────────────────────────────────────────────────
    "sneaker_streetwear": [
        {"handle": "@WillysMadeRare",    "style_tags": ["sneaker_collection", "grid_layout", "clean"],      "why": "Sneaker haul clean grid layout"},
        {"handle": "@KicksDontLie",      "style_tags": ["sneaker_close", "collection", "minimal"],          "why": "Sneaker collection close-up minimal"},
        {"handle": "@TerpsThatTalk",     "style_tags": ["sneaker_unbox", "face_excited", "brand"],          "why": "Sneaker unboxing excited face"},
        {"handle": "@GoreTexHistory",    "style_tags": ["sneaker_tech", "diagram", "clean"],                "why": "Sneaker technology clean diagram"},
        {"handle": "@StreetGearDaily",   "style_tags": ["streetwear_fit", "outfit_flat_lay", "aesthetic"],  "why": "Streetwear outfit flat-lay aesthetic"},
        {"handle": "@HypebeastTV",       "style_tags": ["hype_interview", "face_host", "urban"],             "why": "Hypebeast culture interview style"},
    ],
    # ── Luxury & Wealth ──────────────────────────────────────────────────────
    "luxury_wealth": [
        {"handle": "@AndyHyperX",        "style_tags": ["luxury_car", "cinematic", "high_end"],             "why": "Luxury car cinematic high-end"},
        {"handle": "@LifestyleExplored",  "style_tags": ["rich_person_daily", "face_luxury", "aspirational"],"why": "Wealth lifestyle face aspirational"},
        {"handle": "@LuxuryReviews",     "style_tags": ["product_luxury", "clean_minimal", "gold"],          "why": "Luxury product minimal gold aesthetic"},
        {"handle": "@PrivateJetNetwork", "style_tags": ["private_jet", "aviation_luxury", "cinematic"],      "why": "Private aviation luxury cinematic"},
        {"handle": "@SupercarBlondie",   "style_tags": ["supercar_woman_driver", "face_excited", "speed"],   "why": "Female supercar vlogger excited face"},
        {"handle": "@WatchExpertise",    "style_tags": ["luxury_watch", "close_detail", "clean"],            "why": "Luxury watch detail close-up clean"},
        {"handle": "@DiamondCertified",  "style_tags": ["jewelry_luxury", "sparkle_visual", "minimal"],      "why": "Jewelry luxury sparkle minimal"},
    ],
    # ── Parenting & Family ───────────────────────────────────────────────────
    "parenting_family": [
        {"handle": "@8PassengersReed",   "style_tags": ["family_vlog", "kids_life", "bright"],              "why": "Large family vlog daily life"},
        {"handle": "@SteelHouseFam",     "style_tags": ["couple_kids", "family_moments", "warm"],            "why": "Family moments warm aesthetic"},
        {"handle": "@MomLifeDoctor",     "style_tags": ["parenting_education", "face_mom", "helpful"],       "why": "Parenting education helpful face"},
        {"handle": "@ParentingWithLove", "style_tags": ["child_development", "educational", "clean"],        "why": "Child development education clean"},
        {"handle": "@FamilyFunPack",     "style_tags": ["family_activities", "bright_fun", "kids"],          "why": "Family activities fun bright kids"},
    ],
    # ── Book Reviews & Literature ────────────────────────────────────────────
    "books_literature": [
        {"handle": "@BookTube",          "style_tags": ["book_review", "face_thoughtful", "book_visual"],    "why": "Book review channel thoughtful face"},
        {"handle": "@KristinaHorner",    "style_tags": ["book_haul", "colorful", "aesthetic_shelf"],        "why": "Book haul colorful aesthetic"},
        {"handle": "@BooksWithEmily",    "style_tags": ["literary_essay", "book_stack", "cozy"],            "why": "Literary essay cozy aesthetic"},
        {"handle": "@BookmarksTV",       "style_tags": ["author_interview", "face_serious", "literary"],     "why": "Author interview serious literary"},
        {"handle": "@ReadWithMary",      "style_tags": ["reading_vlog", "book_close", "calming"],           "why": "Reading vlog close-up calming"},
    ],
    # ── ASMR & Relaxation ────────────────────────────────────────────────────
    "asmr_relaxation": [
        {"handle": "@GibiASMR",          "style_tags": ["asmr_roleplay", "close_micro", "whisper"],         "why": "ASMR roleplay close whisper"},
        {"handle": "@ASMRTINGLE",        "style_tags": ["asmr_tapping", "hand_close", "satisfying"],        "why": "ASMR tapping close satisfying"},
        {"handle": "@ClickASMR",         "style_tags": ["asmr_sound_design", "minimal_visual", "trigger"],  "why": "ASMR sound design minimal visual"},
        {"handle": "@RelaxStudio",       "style_tags": ["meditation_asmr", "nature_ambience", "calm"],     "why": "Meditation ASMR calm nature"},
        {"handle": "@SleepStories",      "style_tags": ["bedtime_story", "face_narrator", "soft"],           "why": "Bedtime story narrator soft aesthetic"},
    ],
    # ── Real Estate & Property ───────────────────────────────────────────────
    "real_estate_property": [
        {"handle": "@IanPerbertRealEstate","style_tags": ["home_tour_luxury", "cinematic", "real_estate"],  "why": "Luxury home tour cinematic"},
        {"handle": "@PropertyBrothers",  "style_tags": ["home_renovation", "before_after", "high_energy"],   "why": "Home renovation before/after high energy"},
        {"handle": "@MillionDollarListing","style_tags": ["luxury_property", "expensive_home", "dramatic"],  "why": "Million dollar property dramatic"},
        {"handle": "@RealEstateInvesting","style_tags": ["property_analysis", "chart_data", "clean"],        "why": "Property investment analysis chart"},
        {"handle": "@TinyHouseLiving",   "style_tags": ["small_space", "minimalist_home", "functional"],    "why": "Tiny house minimalist functional"},
    ],
    # ── Reaction Videos ──────────────────────────────────────────────────────
    "reaction_videos": [
        {"handle": "@ReactionMasters",   "style_tags": ["face_reaction", "split_screen", "vocal"],           "why": "Split-screen reaction vocal"},
        {"handle": "@FamousReactors",    "style_tags": ["celebrity_reaction", "face_emotional", "bold"],    "why": "Celebrity reaction emotional"},
        {"handle": "@MetalReaction",     "style_tags": ["musician_reaction", "face_headphones", "intense"], "why": "Musician reaction intense headphones"},
        {"handle": "@JhopeTok",          "style_tags": ["kpop_reaction", "fan_excited", "colorful"],        "why": "K-pop reaction fan excited"},
        {"handle": "@OldGuysReaction",   "style_tags": ["generational_gap", "face_pair", "humor"],          "why": "Generational gap pair humor"},
    ],
    # ── Stock Market & Trading ───────────────────────────────────────────────
    "stock_trading": [
        {"handle": "@InvestAnswers",     "style_tags": ["stock_analysis", "chart_visual", "clean"],         "why": "Stock analysis chart clean visual"},
        {"handle": "@ForexGold",         "style_tags": ["forex_trading", "chart_rapid", "technical"],       "why": "Forex trading rapid chart technical"},
        {"handle": "@OptionsAlpha",      "style_tags": ["options_trading", "graph_data", "professional"],   "why": "Options trading data graph professional"},
        {"handle": "@TrendspotterTV",    "style_tags": ["day_trading", "screen_recording", "intense"],      "why": "Day trading screen recording intense"},
        {"handle": "@DividendGenius",    "style_tags": ["dividend_investing", "passive_income", "calm"],    "why": "Dividend investing passive income calm"},
    ],
    # ── Woodworking & Crafts ─────────────────────────────────────────────────
    "woodworking_crafts": [
        {"handle": "@WoodworkerPro",     "style_tags": ["wood_project", "before_after", "satisfying"],      "why": "Woodworking project satisfying"},
        {"handle": "@CarpentryDaily",    "style_tags": ["tool_work", "close_cut", "satisfying_sound"],     "why": "Carpentry tool work satisfying"},
        {"handle": "@FineWoodworking",   "style_tags": ["furniture_build", "joinery_detail", "professional"],"why": "Fine furniture build professional"},
        {"handle": "@DIYKitchenCabinets","style_tags": ["cabinet_build", "measurement", "organized"],        "why": "Cabinet building organized"},
        {"handle": "@LeatherCrafting",   "style_tags": ["leather_work", "hand_tool", "tactile"],            "why": "Leather crafting hand tool tactile"},
    ],
    # ── Makeup & Beauty ──────────────────────────────────────────────────────
    "makeup_beauty": [
        {"handle": "@JamesCharles",      "style_tags": ["makeup_transformation", "dramatic", "high_energy"], "why": "Makeup transformation dramatic"},
        {"handle": "@NikkieTutorials",   "style_tags": ["makeup_tutorial", "face_glow", "beautiful"],       "why": "Makeup tutorial beautiful face"},
        {"handle": "@MichellePhan",      "style_tags": ["beauty_hack", "creative_makeup", "colorful"],      "why": "Beauty hack creative colorful"},
        {"handle": "@TatiBeauty",        "style_tags": ["makeup_review", "product_close", "detailed"],      "why": "Makeup review detailed product"},
        {"handle": "@BeautyWithEmiUI",   "style_tags": ["makeup_artist", "transformation_bold", "artistic"],"why": "Makeup artist transformation artistic"},
    ],
    # ── Hair Care & Styling ──────────────────────────────────────────────────
    "hair_care": [
        {"handle": "@CaraHairArt",       "style_tags": ["hair_transformation", "bold_color", "dramatic"],    "why": "Hair transformation bold dramatic"},
        {"handle": "@HairstylingTips",   "style_tags": ["hair_tutorial", "close_head", "step_by_step"],     "why": "Hair tutorial step-by-step close"},
        {"handle": "@DogHairMagic",      "style_tags": ["pet_grooming", "before_after", "satisfying"],      "why": "Pet grooming satisfying"},
        {"handle": "@BarbershopASMR",    "style_tags": ["haircut_asmr", "close_sound", "satisfying"],       "why": "Haircut ASMR satisfying sound"},
    ],
    # ── Fashion & Styling ────────────────────────────────────────────────────
    "fashion_styling_deep": [
        {"handle": "@StyleAdvice",       "style_tags": ["outfit_building", "minimalist_closet", "clean"],   "why": "Outfit building minimalist clean"},
        {"handle": "@DesignerArchive",   "style_tags": ["fashion_history", "designer_profile", "elegant"],  "why": "Fashion history designer profile"},
        {"handle": "@VintageHaul",       "style_tags": ["thrift_finds", "treasure_hunt", "colorful"],       "why": "Vintage thrift treasure hunt"},
        {"handle": "@FashionOnBudget",   "style_tags": ["budget_outfits", "cheap_finds", "practical"],      "why": "Budget fashion practical"},
    ],
    # ── Interior Design ──────────────────────────────────────────────────────
    "interior_design_home": [
        {"handle": "@InteriorDesignIdeas","style_tags": ["room_transformation", "before_after", "cinematic"],"why": "Room transformation cinematic"},
        {"handle": "@HomeDecorDIY",      "style_tags": ["decor_project", "affordable", "cozy"],             "why": "Home decor DIY cozy"},
        {"handle": "@MinimalHome",       "style_tags": ["minimalist_space", "clean_lines", "peaceful"],     "why": "Minimalist home peaceful"},
        {"handle": "@VintageInteriors",  "style_tags": ["vintage_decor", "antique_hunt", "aesthetic"],      "why": "Vintage interior aesthetic"},
        {"handle": "@LuxurySuites",      "style_tags": ["high_end_design", "cinematic_tour", "aspirational"],"why": "Luxury design aspirational"},
    ],
    # ── Gardening & Plants ───────────────────────────────────────────────────
    "gardening_plants": [
        {"handle": "@GardenProfile",     "style_tags": ["plant_tour", "green_aesthetic", "peaceful"],       "why": "Plant tour green peaceful"},
        {"handle": "@HousePlantJourney", "style_tags": ["plant_care", "close_leaf", "educational"],        "why": "Plant care educational"},
        {"handle": "@GardenDesignTV",    "style_tags": ["garden_plan", "transformation", "beautiful"],     "why": "Garden design beautiful"},
        {"handle": "@VegetableGarden",   "style_tags": ["growing_food", "harvest_satisfaction", "organic"], "why": "Growing vegetables organic"},
        {"handle": "@SucculentSophia",   "style_tags": ["succulent_collection", "arrangement", "minimal"],  "why": "Succulent collection minimal"},
    ],
    # ── Motorcycles & Bikes ──────────────────────────────────────────────────
    "motorcycles_bikes": [
        {"handle": "@BikeChannelTV",     "style_tags": ["motorcycle_review", "ride_footage", "exciting"],    "why": "Motorcycle review exciting"},
        {"handle": "@MotorcycleCommunity","style_tags": ["bike_culture", "rider_lifestyle", "outdoor"],      "why": "Motorcycle lifestyle outdoor"},
        {"handle": "@MotoVlogCentral",   "style_tags": ["moto_vlog", "helmet_cam", "adventure"],            "why": "Moto vlog adventure helmet cam"},
        {"handle": "@RoadBikePerfect",   "style_tags": ["cycling_tips", "bike_tech", "performance"],        "why": "Cycling tips performance"},
        {"handle": "@MountainBikeLife",  "style_tags": ["mtb_ride", "trail_footage", "adrenaline"],        "why": "Mountain bike trail adrenaline"},
    ],
    # ── Aquascaping & Fish ───────────────────────────────────────────────────
    "aquascaping_fish": [
        {"handle": "@AquascapeLife",     "style_tags": ["aquatic_garden", "plant_arrangement", "beautiful"], "why": "Aquascaping beautiful arrangement"},
        {"handle": "@FishKeepingFacts",  "style_tags": ["fish_care", "educational", "calm"],                "why": "Fish care educational calm"},
        {"handle": "@TankTutorials",     "style_tags": ["aquarium_setup", "step_by_step", "detailed"],      "why": "Aquarium setup detailed"},
        {"handle": "@ReefLife",          "style_tags": ["coral_reef", "saltwater", "colorful"],             "why": "Coral reef colorful"},
    ],
    # ── 3D Printing & Robotics ───────────────────────────────────────────────
    "3d_printing_robotics": [
        {"handle": "@3DPrintingDaily",   "style_tags": ["3d_print_result", "object_reveal", "satisfying"],  "why": "3D printing reveal satisfying"},
        {"handle": "@RoboticsToday",     "style_tags": ["robot_demo", "ai_visual", "futuristic"],           "why": "Robotics demo futuristic"},
        {"handle": "@3DPrintFails",      "style_tags": ["printing_error", "comedy_fail", "learning"],       "why": "3D print fails comedy"},
        {"handle": "@CNC_Shop",          "style_tags": ["cnc_machine", "tool_work", "precision"],           "why": "CNC machining precision"},
    ],
    # ── Drones & Aerial ──────────────────────────────────────────────────────
    "drones_aerial": [
        {"handle": "@DronePilotTV",      "style_tags": ["drone_footage", "cinematic_aerial", "beautiful"],  "why": "Drone footage cinematic beautiful"},
        {"handle": "@FPVFlying",         "style_tags": ["fpv_drone_race", "high_speed", "intense"],         "why": "FPV racing intense"},
        {"handle": "@DroneReviewPro",    "style_tags": ["drone_comparison", "tech_specs", "detailed"],      "why": "Drone review detailed"},
        {"handle": "@AerialPhotography", "style_tags": ["landscape_aerial", "cinematic_nature", "stunning"], "why": "Landscape aerial stunning"},
    ],
    # ── Vintage & Restoration ────────────────────────────────────────────────
    "vintage_restoration": [
        {"handle": "@RestoreChannel",    "style_tags": ["object_restoration", "before_after", "satisfying"], "why": "Restoration satisfying"},
        {"handle": "@VintageFinds",      "style_tags": ["antique_hunt", "treasure", "discovery"],           "why": "Antique hunting discovery"},
        {"handle": "@ClassicCarRestore", "style_tags": ["car_restoration", "old_to_new", "impressive"],     "why": "Classic car restoration"},
        {"handle": "@VintageAudio",      "style_tags": ["speaker_restore", "sound_quality", "nostalgia"],   "why": "Vintage audio restoration"},
    ],
    # ── Minimalism & Decluttering ────────────────────────────────────────────
    "minimalism_organization": [
        {"handle": "@MinimalistLife",    "style_tags": ["decluttering_process", "before_after", "peaceful"], "why": "Decluttering peaceful"},
        {"handle": "@OrganizeWithMarie", "style_tags": ["organization_method", "tidy_space", "calm"],        "why": "Organization calm method"},
        {"handle": "@SimpleStorage",     "style_tags": ["storage_solutions", "practical", "functional"],     "why": "Storage solutions functional"},
        {"handle": "@ZeroWaste",         "style_tags": ["sustainable_living", "eco", "conscious"],          "why": "Sustainable living conscious"},
    ],
    # ── Content Creator Deep Dive ────────────────────────────────────────────
    "content_creation_business": [
        {"handle": "@CreatorAcademy",    "style_tags": ["youtube_strategy", "growth_tactics", "educational"],"why": "YouTube education growth"},
        {"handle": "@VideoEditingMastery","style_tags": ["editing_tutorial", "before_after", "professional"], "why": "Video editing professional"},
        {"handle": "@AudioEngineer",     "style_tags": ["sound_design", "mixing", "technical"],             "why": "Audio engineering technical"},
        {"handle": "@StreamSetup",       "style_tags": ["streaming_gear", "setup_tour", "organized"],       "why": "Streaming setup organized"},
        {"handle": "@CreatorTools",      "style_tags": ["software_review", "workflow", "efficient"],         "why": "Creator tools efficient"},
    ],
    # ── Architecture & Urban Planning ────────────────────────────────────────
    "architecture_urban": [
        {"handle": "@ArchitectureWalks", "style_tags": ["building_tour", "design_analysis", "educational"], "why": "Architecture tour educational"},
        {"handle": "@UrbanDesignFuture", "style_tags": ["city_planning", "innovation", "futuristic"],       "why": "Urban design futuristic"},
        {"handle": "@BuiltEnvironment",  "style_tags": ["infrastructure", "documentary", "impressive"],     "why": "Infrastructure documentary"},
        {"handle": "@SkyscraperLife",    "style_tags": ["tall_building", "construction", "scale"],          "why": "Skyscraper construction scale"},
    ],
    # ── Personal Finance Details ─────────────────────────────────────────────
    "personal_finance_deep": [
        {"handle": "@DebtFreeJourney",   "style_tags": ["debt_payoff", "motivation", "progress"],           "why": "Debt payoff journey motivation"},
        {"handle": "@BudgetingHacks",    "style_tags": ["money_saving", "practical_tips", "relatable"],     "why": "Budgeting practical tips"},
        {"handle": "@RetirementPlan",    "style_tags": ["retirement_strategy", "compound", "educational"],   "why": "Retirement education compound"},
        {"handle": "@NetWorthTracking",  "style_tags": ["wealth_building", "progress_update", "inspiring"],  "why": "Wealth building inspiring"},
    ],
    # ── Podcast Clips & Highlights ───────────────────────────────────────────
    "podcast_clips": [
        {"handle": "@ClipsDaily",        "style_tags": ["podcast_moment", "highlight_viral", "bold_text"],  "why": "Podcast clip viral highlight"},
        {"handle": "@TalkShowClips",     "style_tags": ["interview_highlight", "face_reaction", "engaging"], "why": "Interview clip engaging"},
        {"handle": "@ComedyHighlights",  "style_tags": ["stand_up_clip", "laugh_moment", "funny"],          "why": "Comedy highlight funny"},
        {"handle": "@PodcastWisdom",     "style_tags": ["quote_visual", "motivation", "text_overlay"],      "why": "Podcast wisdom motivation"},
    ],
    # ── Mukbang & Food Content ───────────────────────────────────────────────
    "mukbang_food_asmr": [
        {"handle": "@AsmrEating",        "style_tags": ["eating_asmr", "close_mouth", "satisfying"],        "why": "Eating ASMR satisfying"},
        {"handle": "@RestaurantReview",  "style_tags": ["food_review", "taste_reaction", "honest"],         "why": "Restaurant review honest"},
        {"handle": "@StreetFoodMaster",  "style_tags": ["street_food", "cooking_live", "sizzle"],          "why": "Street food cooking"},
        {"handle": "@PastryMaking",      "style_tags": ["baking_process", "pastry_close", "satisfying"],    "why": "Pastry making satisfying"},
    ],
    # ── Anime & Manga Deep Dive ──────────────────────────────────────────────
    "anime_manga": [
        {"handle": "@AnimeAnalysis",     "style_tags": ["anime_review", "scene_breakdown", "critical"],     "why": "Anime analysis critical"},
        {"handle": "@MangaExplained",    "style_tags": ["manga_chapter", "story_visual", "engaging"],       "why": "Manga explained engaging"},
        {"handle": "@AnimeCompilation",  "style_tags": ["best_moments", "scene_clip", "epic"],              "why": "Anime compilation epic"},
        {"handle": "@AnimeStudio",       "style_tags": ["animation_process", "behind_scenes", "educational"],"why": "Animation process educational"},
    ],
    # ── Productivity & Time Management ───────────────────────────────────────
    "productivity_time": [
        {"handle": "@ProductivityHacks",  "style_tags": ["routine_build", "workflow", "efficient"],         "why": "Productivity routine efficient"},
        {"handle": "@TimeManagement",     "style_tags": ["schedule_planner", "calendar", "organized"],      "why": "Time management organized"},
        {"handle": "@FocusMethod",        "style_tags": ["deep_work", "technique", "educational"],          "why": "Focus technique educational"},
        {"handle": "@HabitBuilding",      "style_tags": ["daily_habit", "progress", "motivational"],       "why": "Habit building motivational"},
    ],
}


def seed_registry(
    force: bool = False,
    on_progress: Callable[[str], None] | None = None,
) -> dict:
    """Resolve all curated handles and write them into channels_registry.yml.

    Skips channels that are already in the registry unless force=True.
    Returns {"resolved": N, "skipped": N, "failed": [handles]}.
    """
    from scraper.registry_manager import add_channel, load_registry
    from scraper.youtube_scraper import ReferenceScraper

    def log(msg: str) -> None:
        print(f"[registry-seeder] {msg}")
        if on_progress:
            on_progress(msg)

    reg = load_registry()
    scraper = ReferenceScraper.from_config()
    resolved = 0
    skipped = 0
    failed: list[str] = []

    for niche, channels in CURATED_CHANNELS.items():
        existing_names = {
            ch["name"].lower()
            for ch in reg.get(niche, {}).get("channels", [])
        }
        for ch in channels:
            handle = ch["handle"].lstrip("@")
            if handle.lower() in existing_names and not force:
                skipped += 1
                continue

            log(f"  resolving {ch['handle']} [{niche}]…")
            result = scraper.resolve_handle(ch["handle"])
            if not result:
                log(f"  [warn] could not resolve {ch['handle']}")
                failed.append(ch["handle"])
                continue

            add_channel(
                niche,
                result["title"],
                result["channel_id"],
                ch["style_tags"],
                ch["why"],
            )
            resolved += 1
            log(f"    → {result['title']} ({result['channel_id']})")

    log(f"Done. {resolved} resolved, {skipped} skipped, {len(failed)} failed.")
    return {"resolved": resolved, "skipped": skipped, "failed": failed}
