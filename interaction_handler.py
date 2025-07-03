import sys
import os
import re
import random
import datetime
import openai
from dotenv import load_dotenv
from scaffolding_selector import ScaffoldingSelector
from response_generator import ResponseGenerator

# Load environment variables from the specific .env file
load_dotenv('test-interaction.env')

class StoryInteractionHandler:
    # Class-level constants
    PRE_STORY_PROMPT_PATH = "prompts/pre_story_prompt.txt"
    CHILD_NAME = "Caro"  # Fixed child name
    
    # Adventure themes for pre-story interaction
    ADVENTURE_THEMES = [
        "A famous landmark on earth (like the Eiffel Tower or Great Wall of China)",
        "A well-known celestial body (like the Moon or Mars)",
        "An everyday location (like a farm or playground)",
        "A natural biome (like a rainforest or desert)"
    ]

    def __init__(self, story_file_path, api_key=None, max_interaction_depth=3, response_length="short", test_mode=False):
        """
        Initialize the story interaction handler.
        
        Args:
            story_file_path: Path to the story file
            api_key: OpenAI API key (optional if set in environment)
            max_interaction_depth: Maximum depth of follow-up questions
            response_length: 'short' for 1-2 sentence responses or 'standard' for original behavior
            test_mode: If True, skips to the last interaction for testing
        """
        self.story_file_path = story_file_path
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.max_interaction_depth = max_interaction_depth
        self.ending_max_depth = 5  # Includes 1 initial + 4 follow-ups = 5 total questions
        self.ending_depth_map = {
            "story_retelling": 6,  # Allows for more detailed retelling
            "alternative_ending": 5,
            "response_summary_closure": 5
        }
        self.response_length = response_length
        self.test_mode = test_mode
        self.child_name = self.CHILD_NAME  # Use fixed child name
        self.child_responses = []  # Track child's responses for personalization
        self.chosen_ending_type = None  # Store the chosen ending type for summary interactions
        self.chosen_theme = None  # Store the chosen adventure theme
        
        # Define special tags that aren't vocabulary words but structural indicators
        self.special_tags = ["summary"]
        
        # Load vocabulary sets
        self.vocab_sets = self.load_vocab_sets()
        
        if not self.api_key:
            raise ValueError("OpenAI API key is missing! Please provide it as an argument or in .env file.")
        
        # Initialize OpenAI client for greeting generation
        self.client = openai.OpenAI(api_key=self.api_key)
        
        self.scaffolding_selector = ScaffoldingSelector()
        # Use the improved ResponseGenerator with the specified response length
        self.response_generator = ResponseGenerator(api_key=self.api_key, response_length=self.response_length)
        
        # Load pre-story prompt template
        try:
            with open(self.PRE_STORY_PROMPT_PATH, 'r') as f:
                self.pre_story_template = f.read()
        except FileNotFoundError:
            print(f"Warning: Could not find {self.PRE_STORY_PROMPT_PATH}. Using default pre-story interaction.")
            self.pre_story_template = None
        
        self.story_content = self.load_story()
        self.story_sections = self.parse_story()
        self.story_log = []
        
        # Start with pre-story interaction
        self.pre_story_interaction()
        
    def load_vocab_sets(self):
        """
        Load vocabulary sets from external files.
        First tries to load from vocab_sets.txt, then falls back to random_selector.py approach.
        """
        vocab_sets = []
        
        # Try to load from vocab_sets.txt first
        vocab_sets_path = "storyGenerator-main 2/vocab_sets.txt"
        if os.path.exists(vocab_sets_path):
            try:
                with open(vocab_sets_path, 'r') as file:
                    for line in file:
                        line = line.strip()
                        if line:  # Skip empty lines
                            words = line.split()
                            if len(words) == 3:  # Ensure we have exactly 3 words
                                vocab_sets.append(words)
                print(f"Loaded {len(vocab_sets)} vocabulary sets from {vocab_sets_path}")
                return vocab_sets
            except Exception as e:
                print(f"Warning: Could not load vocab_sets.txt: {e}")
        
        # Fallback: try to load from random_selector.py approach
        try:
            # Set A: Easy + Review vocabs
            set_a = [
                "ant", "aunt", "baseball", "bend", "boy", "bunch", "candle", "cent", "chirp", "coach",
                "cow", "cuddle", "delicious", "divide", "duck", "empty", "far", "flash", "fresh", "garden",
                "glue", "grumble", "healthy", "hole", "ice", "jeans", "kind", "leaf", "lock", "magnet",
                "milk", "mother", "near", "nose", "pain", "path", "piano", "plastic", "pour", "quack",
                "raw", "rink", "rude", "scissors", "ship", "skunk", "sneeze", "sparkle", "stair", "strong",
                "tall", "thirsty", "town", "tumble", "usual", "waddle", "week", "winter", "xylophone", "zoo"
            ]
            
            # Set B: New vocabs
            set_b = [
                "alligator", "ambulance", "breakfast", "commercial", "disguise", "earthquake",
                "emergency", "freckle", "frisky", "glitter", "hibernate", "hurricane",
                "invisible", "kindergarten", "lifeguard", "meteor", "nickname", "opposite",
                "permission", "pollution", "quarrel", "restaurant", "sentence", "treasure", 
                "umbrella", "valentine", "vocabulary", "whisper", "yesterday", "zigzag"
            ]
            
            # Generate some vocabulary sets dynamically
            for _ in range(30):  # Generate 30 sets
                selected_from_a = random.sample(set_a, 2)
                selected_from_b = random.choice(set_b)
                # Arrange in the specified order: <easy_word> <new_word> <review_word>
                vocab_set = [selected_from_a[0], selected_from_b, selected_from_a[1]]
                vocab_sets.append(vocab_set)
            
            print(f"Generated {len(vocab_sets)} vocabulary sets using fallback method")
            return vocab_sets
            
        except Exception as e:
            print(f"Warning: Could not generate vocabulary sets: {e}")
            # Final fallback - minimal set
            return [["ant", "alligator", "baseball"], ["cow", "emergency", "duck"], ["garden", "hurricane", "ice"]]

    def load_story(self):
        with open(self.story_file_path, 'r') as file:
            return file.read()
    
    def parse_story(self):
        """
        Parse the story content to extract interactions and their vocabulary targets.
        The format for interactions is: <interaction vocab="target_word" role="vocab_role">Prompt text</interaction>
        Special tags like "summary" are identified and treated differently.
        """
        # Updated pattern to extract vocab attribute and role
        interaction_pattern = r'<interaction(?: vocab="([^"]*)")?(?:\s+role="([^"]*)")?>([^<]*)</interaction>'
        interaction_matches = list(re.finditer(interaction_pattern, self.story_content, re.DOTALL))
        
        sections = []
        
        if not interaction_matches:
            return [{"text": self.story_content, "prompt": None, "vocab": None, "vocab_role": None, "special_tag": None}]
        
        last_end = 0
        for i, match in enumerate(interaction_matches):
            interaction_start = match.start()
            interaction_end = match.end()
            vocab = match.group(1) if match.group(1) else None  # Extract the vocab
            vocab_role = match.group(2) if match.group(2) else None  # Extract the vocab role
            prompt = match.group(3).strip()
            
            # Determine if this is a special tag or a vocabulary target
            special_tag = None
            target_vocab = None
            if vocab in self.special_tags:
                special_tag = vocab
            elif vocab:
                target_vocab = vocab
            
            text_before = self.story_content[last_end:interaction_start]
            full_display_text = text_before + f"<interaction>{prompt}</interaction>"
            
            # Use the full story content as context to ensure comprehensive understanding
            full_story_before = self.story_content[:interaction_start]
            full_story_after = self.story_content[interaction_end:]
            
            sections.append({
                "text": full_display_text,
                "prompt": prompt,
                "vocab": target_vocab,
                "vocab_role": vocab_role,
                "special_tag": special_tag,
                "context_before": full_story_before,
                "context_after": full_story_after
            })
            
            last_end = interaction_end
        
        if last_end < len(self.story_content):
            sections.append({
                "text": self.story_content[last_end:],
                "prompt": None,
                "vocab": None,
                "vocab_role": None,
                "special_tag": None,
                "context_before": "",
                "context_after": ""
            })
        
        return sections
    
    def remove_emojis(self, text):
        # Remove all emoji characters from the text
        emoji_pattern = re.compile(
            "["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map symbols
            u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
            u"\U00002700-\U000027BF"  # Dingbats
            u"\U000024C2-\U0001F251"  # Enclosed characters
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub(r'', text)

    def extract_story_vocabs(self):
        """Extract the three main vocab words from the story's interaction tags (excluding 'summary')."""
        vocab_words = []
        pattern = r'<interaction(?: vocab="([^"]*)")(?:\s+role="([^"]*)")?>([^<]*)</interaction>'
        matches = re.findall(pattern, self.story_content)
        for vocab, role, _ in matches:
            if vocab and vocab != 'summary' and vocab not in vocab_words:
                vocab_words.append(vocab)
            if len(vocab_words) == 3:
                break
        return vocab_words if len(vocab_words) == 3 else None

    def select_target_words(self):
        """
        Select 3 target words for the pre-story interaction.
        If the story file is loaded, extract the vocab words from the story.
        Otherwise, use a random vocab set.
        """
        story_vocabs = self.extract_story_vocabs() if hasattr(self, 'story_content') else None
        if story_vocabs:
            return story_vocabs
        elif self.vocab_sets:
            return random.choice(self.vocab_sets)
        else:
            return ["story", "adventure", "fun"]

    def pre_story_interaction(self):
        if not self.pre_story_template:
            self._basic_pre_story_interaction()
            return

        print("\n=== Pre-story interaction ===\n")

        # Get target words from the story file if possible
        words = self.select_target_words()
        self.chosen_theme = None
        prompt = self.pre_story_template.format(
            child_name=self.child_name,
            word1=words[0],
            word2=words[1],
            word3=words[2]
        )
        try:
            # 1. Warm check-in (with variety)
            checkin_templates = [
                "Hello {name}! I danced under a rainbow this morning—what colorful thing did you see today?",
                "Hey {name}, I baked magical cookies in my kitchen—did you taste anything yummy today?",
                "Good day, {name}! I met a tiny bee in the garden—what small creature did you notice today?",
                "Hi {name}! I built a towering block castle—what did you build or create today?",
                "Hello {name}, I splashed in a puddle after the rain—did you play in the water or the mud today?",
                "Hey {name}! I sang a silly song with my toy duck—what tune did you sing or hum today?",
                "Hi {name}! I painted a picture of a friendly dragon—did you draw or color anything today?",
                "Hello {name}, I was a superhero saving kittens—who did you help or play with today?",
                "Hey {name}! I explored a secret cave of sparkly crystals—did you discover something new today?",
                "Good morning, {name}! I counted five jumping frogs at the pond—what numbers did you notice today?",
                "Hi {name}! I met a robot friend at the playground—who did you meet or play with today?",
                "Hello {name}, I floated a paper boat on a little stream—did you play with any toys outside today?",
                "Hey {name}! I learned a new animal sound from a parrot—what new sound or word did you learn today?",
                "Good day, {name}! I chased butterflies in a sunny meadow—what made you feel happy or free today?",
                "Hi {name}! I visited a snowy mountain in my magical world—did you go on any adventures today?",
                "Hello {name}, I found a shiny seashell at the beach—did you collect or find anything neat today?",
                "Hey {name}! I planted a magical seed and watched it grow—what did you help grow or take care of today?",
                "Good morning, {name}! I flew over a city in a paper airplane—what fun did you have with friends today?",
                "Hi {name}! I spotted a bright rainbow after a storm—what beautiful colors did you see today?",
            ]
            # Split each prompt into (experience, question)
            experiences = [s.split('—')[0].strip() for s in checkin_templates]
            questions = [s.split('—')[1].strip() if '—' in s else s for s in checkin_templates]
            idx = random.randrange(len(checkin_templates))
            chosen_experience = experiences[idx].replace('{name}', self.child_name)
            chosen_checkin = questions[idx]
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Start by sharing this experience: '{chosen_experience}' and then ask: '{chosen_checkin}'"}
                ],
                max_tokens=100,
                temperature=0.7
            )
            check_in = self.remove_emojis(response.choices[0].message.content.strip())
            print(f"Ella: {check_in}")
            self.story_log.append(f"Ella: {check_in}")
            child_response = input(f"{self.child_name}: ")
            self.story_log.append(f"Child: {child_response}")

            # ————————————————
            # If the child asks a question, have the LLM answer it briefly and positively:
            child_asked_question, child_question, _ = self.contains_question(child_response)
            if child_asked_question and child_question:
                resp = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content":
                         "You are Ella, a caring robot. Please answer the child's question "
                         "in one short, happy, encouraging sentence."
                        },
                        {"role": "user", "content": child_question}
                    ],
                    max_tokens=30,
                    temperature=0.8
                )
                quick = self.remove_emojis(resp.choices[0].message.content.strip())
                print(f"Ella: {quick}")
                self.story_log.append(f"Ella: {quick}")

            # 2. Adventure intro (personalized, smooth transition)
            # Acknowledge the child's response
            ack_templates = [
                f"That's wonderful, {self.child_name}!",
                f"How exciting, {self.child_name}!",
                f"That makes me happy to hear, {self.child_name}!",
                f"I'm so glad you shared that, {self.child_name}!"
            ]
            ack = random.choice(ack_templates)
            # Rainbow button line (varied)
            rainbow_templates = [
                "You know, I love adventures too! I have this magical rainbow button that takes me anywhere I want!",
                "Guess what? My magical rainbow button lets me visit the most amazing places!",
                "I have a special rainbow button that can take us to any place we imagine!",
                "My magical rainbow button helps me explore all sorts of wonderful places!"
            ]
            rainbow_line = random.choice(rainbow_templates)
            # Segue to theme choice (varied)
            segue_templates = [
                "Let's choose our next adventure together!",
                "Now, let's pick a place to visit!",
                "Which adventure should we go on today?",
                "You get to choose where we go next!"
            ]
            segue = random.choice(segue_templates)
            adventure_intro = f"{ack} {rainbow_line} {segue}"
            adventure_intro = self.remove_emojis(adventure_intro)
            print(f"Ella: {adventure_intro}")
            self.story_log.append(f"Ella: {adventure_intro}")

            # 3. Theme choice (present only two random themes, add examples after each)
            theme_examples = {
                "A famous landmark on earth (like the Eiffel Tower or Great Wall of China)": "(like the Eiffel Tower or Great Wall of China)",
                "A well-known celestial body (like the Moon or Mars)": "(like the Moon or Mars)",
                "An everyday location (like a farm or playground)": "(like a farm or playground)",
                "A natural biome (like a rainforest or desert)": "(like a rainforest or desert)"
            }
            two_themes = random.sample(self.ADVENTURE_THEMES, 2)
            # Only print the two theme choices, nothing else
            for i, theme in enumerate(two_themes, 1):
                base = theme.split('(')[0].strip()
                example = theme_examples.get(theme, None)
                if example:
                    print(f"{i}. {base} {example}")
                else:
                    print(f"{i}. {base}")
            while True:
                child_theme = input(f"{self.child_name}: ").strip().lower()
                matches = [theme for theme in two_themes if child_theme in theme.lower()]
                if not matches:
                    matches = [theme for theme in two_themes if any(word in theme.lower() for word in child_theme.split())]
                if matches:
                    self.chosen_theme = matches[0]
                    break
                else:
                    print("Ella: That sounds fun! Can you say a few words from the theme you want?")
            self.story_log.append(f"Child: {self.chosen_theme}")

            # 4. Theme acknowledgment (short, direct transition to game)
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Show excitement about their choice of {self.chosen_theme} and then say: 'Let's get ready with our magic words!'"}
                ],
                max_tokens=60,
                temperature=0.7
            )
            raw_theme_ack = response.choices[0].message.content.strip()
            theme_ack = self.remove_emojis(raw_theme_ack)
            print(f"Ella: {theme_ack}")
            self.story_log.append(f"Ella: {theme_ack}")

            # 5. Magic word game (use the actual story vocab, check correctness)
            game_styles = [
                "Magic Word Unlock",
                "Robot Freeze Game",
                "Story Hat Chooser",
                "Oops! Wrong Story!"
            ]
            chosen_style = random.choice(game_styles)
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Introduce the magic word game using the {chosen_style} style. Make it playful and engaging, but do NOT mention or list any of the magic words. Only say that you need three magic words to unlock the story, and ask if the child is ready. Only output a single, short introduction sentence."}
                ],
                max_tokens=60,
                temperature=0.7
            )
            raw_game_intro = response.choices[0].message.content.strip().split('\n')[0]
            game_intro = self.remove_emojis(raw_game_intro)
            print(f"Ella: {game_intro}")
            self.story_log.append(f"Ella: {game_intro}")
            for idx, word in enumerate(words):
                ordinal = ["first", "second", "third"][idx]
                # First attempt
                print(f"Ella: The {ordinal} magic word is '{word}'. Can you say '{word}'?")
                self.story_log.append(f"Ella: The {ordinal} magic word is '{word}'. Can you say '{word}'?")
                word_response = input(f"{self.child_name}: ")
                self.story_log.append(f"Child: {word_response}")
                
                # If first attempt is wrong, give one retry
                if word_response.strip().lower() != word.lower():
                    retry_templates = [
                        f"Oh, I didn't catch that. Could you please say '{word}' again?",
                        f"Hmm, I couldn't quite hear you. Can you say '{word}' one more time?",
                        f"Sorry, I missed that. Would you say '{word}' again for me?",
                        f"Oops, I didn't hear that clearly. Could you repeat '{word}'?"
                    ]
                    retry_prompt = random.choice(retry_templates)
                    retry_prompt = self.remove_emojis(retry_prompt)
                    print(f"Ella: {retry_prompt}")
                    self.story_log.append(f"Ella: {retry_prompt}")
                    word_response = input(f"{self.child_name}: ")
                    self.story_log.append(f"Child: {word_response}")
                # Only give special praise after the last word
                if idx == 2:
                    response = self.client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": prompt},
                            {"role": "user", "content": f"Give a special, enthusiastic praise for the child saying all three magic words, referencing their last response: '{word_response}'. Celebrate unlocking the story together!"}
                        ],
                        max_tokens=60,
                        temperature=0.7
                    )
                    encouragement = self.remove_emojis(response.choices[0].message.content.strip())
                    print(f"Ella: {encouragement}")
                    self.story_log.append(f"Ella: {encouragement}")

            # 6. Story bridge (short, direct, varied transition)
            story_bridges = [
                f"Let me tell you what happened on my journey!",
                f"Now, let me tell you my magical story!",
                f"Here's what happened on my adventure!",
                f"Let's dive into my story and see what I discovered!"
            ]
            story_bridge = random.choice(story_bridges)
            story_bridge = self.remove_emojis(story_bridge)
            print(f"Ella: {story_bridge}")
            self.story_log.append(f"Ella: {story_bridge}")

            print("\n=== Starting interactive story session...===\n")

        except Exception as e:
            print(f"Warning: Could not complete LLM-guided pre-story interaction: {e}")
            print("Falling back to basic pre-story interaction...")
            self._basic_pre_story_interaction()

    def _basic_pre_story_interaction(self):
        # 1) DAILY CHECK-IN (Ella sharing her excitement)
        checkins = [
            "Hello {name}! I danced under a rainbow this morning—what colorful thing did you see today?",
            "Hey {name}, I baked magical cookies in my kitchen—did you taste anything yummy today?",
            "Good day, {name}! I met a tiny bee in the garden—what small creature did you notice today?",
            "Hi {name}! I built a towering block castle—what did you build or create today?",
            "Hello {name}, I splashed in a puddle after the rain—did you play in the water or the mud today?",
            "Hey {name}! I sang a silly song with my toy duck—what tune did you sing or hum today?",
            "Hi {name}! I painted a picture of a friendly dragon—did you draw or color anything today?",
            "Hello {name}, I was a superhero saving kittens—who did you help or play with today?",
            "Hey {name}! I explored a secret cave of sparkly crystals—did you discover something new today?",
            "Good morning, {name}! I counted five jumping frogs at the pond—what numbers did you notice today?",
            "Hi {name}! I met a robot friend at the playground—who did you meet or play with today?",
            "Hello {name}, I floated a paper boat on a little stream—did you play with any toys outside today?",
            "Hey {name}! I learned a new animal sound from a parrot—what new sound or word did you learn today?",
            "Good day, {name}! I chased butterflies in a sunny meadow—what made you feel happy or free today?",
            "Hi {name}! I visited a snowy mountain in my magical world—did you go on any adventures today?",
            "Hello {name}, I found a shiny seashell at the beach—did you collect or find anything neat today?",
            "Hey {name}! I planted a magical seed and watched it grow—what did you help grow or take care of today?",
            "Good morning, {name}! I flew over a city in a paper airplane—what fun did you have with friends today?",
            "Hi {name}! I spotted a bright rainbow after a storm—what beautiful colors did you see today?",
        ]
        checkin_prompt = random.choice(checkins).format(name=self.child_name)
        checkin_prompt = self.remove_emojis(checkin_prompt)
        print(f"Ella: {checkin_prompt}")
        self.story_log.append(f"Ella: {checkin_prompt}")
        checkin_answer = input(f"{self.child_name}: ")
        self.story_log.append(f"Child: {checkin_answer}")

        # 2) ACKNOWLEDGE AND INTRODUCE ADVENTURES (personalized, smooth transition)
        ack = f"That's wonderful, {self.child_name}! I love hearing about your day and your story about '{checkin_answer}'. You know, I absolutely love adventures too! Now, let me share some of my past adventures with you. You can choose which one you like!"
        ack = self.remove_emojis(ack)
        print(f"Ella: {ack}")
        self.story_log.append(f"Ella: {ack}")

        # 3) PRESENT THEME CHOICES (only two, add examples after each)
        theme_examples = {
            "A famous landmark on earth (like the Eiffel Tower or Great Wall of China)": "(like the Eiffel Tower or Great Wall of China)",
            "A well-known celestial body (like the Moon or Mars)": "(like the Moon or Mars)",
            "An everyday location (like a farm or playground)": "(like a farm or playground)",
            "A natural biome (like a rainforest or desert)": "(like a rainforest or desert)"
        }
        two_themes = random.sample(self.ADVENTURE_THEMES, 2)
        # Only print the two theme choices, nothing else
        for i, theme in enumerate(two_themes, 1):
            base = theme.split('(')[0].strip()
            example = theme_examples.get(theme, None)
            if example:
                print(f"{i}. {base} {example}")
            else:
                print(f"{i}. {base}")
        while True:
            try:
                choice = int(input(f"\n{self.child_name}: "))
                if 1 <= choice <= 2:
                    self.chosen_theme = two_themes[choice-1]
                    break
                else:
                    print("Ella: Oops! Please choose 1 or 2!")
            except ValueError:
                print("Ella: Please enter 1 or 2!")
        self.story_log.append(f"Child: {self.chosen_theme}")

        # 4) INTRODUCE MAGIC WORDS (use actual story vocab, check correctness)
        magic_intro = "Let's say the three special magic words together!"
        magic_intro = self.remove_emojis(magic_intro)
        print(f"Ella: {magic_intro}")
        self.story_log.append(f"Ella: {magic_intro}")

        words = self.select_target_words()
        encouraging_responses = [
            "Perfect! That's exactly how I remember it!",
            "Excellent! You're helping me remember so well!",
            "Beautiful! That's just how it sounded in my adventure!",
            "Wonderful! You're making the magic words come alive!",
            "Great job! You're helping me remember my special day!",
            "Amazing! That's exactly how I felt during my adventure!"
        ]

        for i, word in enumerate(words):
            ordinal = ["first", "second", "third"][i]
            # First attempt
            print(f"Ella: The {ordinal} magic word is '{word}'. Can you say '{word}'?")
            self.story_log.append(f"Ella: The {ordinal} magic word is '{word}'. Can you say '{word}'?")
            reply = input(f"{self.child_name}: ")
            self.story_log.append(f"Child: {reply}")
            
            # If first attempt is wrong, give one retry
            if reply.strip().lower() != word.lower():
                retry_templates = [
                    f"Oh, I didn't catch that. Could you please say '{word}' again?",
                    f"Hmm, I couldn't quite hear you. Can you say '{word}' one more time?",
                    f"Sorry, I missed that. Would you say '{word}' again for me?",
                    f"Oops, I didn't hear that clearly. Could you repeat '{word}'?"
                ]
                retry_prompt = random.choice(retry_templates)
                retry_prompt = self.remove_emojis(retry_prompt)
                print(f"Ella: {retry_prompt}")
                self.story_log.append(f"Ella: {retry_prompt}")
                reply = input(f"{self.child_name}: ")
                self.story_log.append(f"Child: {reply}")
            if i < len(words) - 1:
                encouragement = random.choice(encouraging_responses)
                encouragement = self.remove_emojis(encouragement)
                print(f"Ella: {encouragement}")
                self.story_log.append(f"Ella: {encouragement}")
        # 6) STORY BRIDGE (short, direct, varied transition)
        story_transitions = [
            f"Let me tell you what happened on my journey!",
            f"Now, let me tell you my magical story!",
            f"Here's what happened on my adventure!",
            f"Let's dive into my story and see what I discovered!"
        ]
        story_transition = random.choice(story_transitions)
        story_transition = self.remove_emojis(story_transition)
        print(f"Ella: {story_transition}")
        self.story_log.append(f"Ella: {story_transition}")

    def get_greeting(self):
        """Generate a time-appropriate greeting."""
        current_hour = datetime.datetime.now().hour
        
        if 5 <= current_hour < 12:
            greeting = "Good morning"
        elif 12 <= current_hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"
            
        if self.child_name:
            greeting += f", {self.child_name}"
        
        greeting += "! "
        
        return greeting


    def contains_question(self, text):
        """
        Check if text contains a question, with improved detection of question-like phrases.
        Uses regex to handle various question formats and edge cases.
        
        Args:
            text: The text to check
            
        Returns:
            Tuple of (is_question, pre_question, post_question)
        """
        if not text or not text.strip():
            return False, None, None
            
        # Clean the text
        clean_text = text.strip()
        
        # First check for explicit question marks with regex
        question_pattern = r"[A-Za-z0-9][^.!?]*\?\s*$"
        question_match = re.search(question_pattern, clean_text)
        if question_match:
            question_text = question_match.group(0)
            pre_question = clean_text[:clean_text.find(question_text) + len(question_text)]
            post_question = clean_text[clean_text.find(question_text) + len(question_text):]
            return True, pre_question, post_question
            
        # Check for implicit question patterns
        implicit_question_patterns = [
            r"tell me", r"can you", r"would you", r"could you",
            r"imagine", r"describe", r"explain", r"share",
            r"think about", r"remember", r"recall",
            r"what if", r"how about", r"let's talk about"
        ]
        
        for pattern in implicit_question_patterns:
            if re.search(rf"\b{pattern}\b", clean_text.lower()):
                return True, clean_text, ""
            
        # Fallback: check for question-like phrases
        question_phrases = [
            r"^how\b", r"^what\b", r"^why\b", r"^who\b", r"^when\b", r"^where\b",
            r"^can you\b", r"^would you\b", r"^could you\b", r"^do you\b",
            r"^tell me about\b", r"^describe\b", r"^explain\b",
            r"^what do you think\b", r"^what if\b", r"^imagine if\b",
            r"^remember\b", r"^recall\b", r"^think about\b",
            r"^can you tell me\b", r"^would you like to\b",
            r"^what was your favorite\b", r"^how did you feel\b"
        ]
        
        # Check for question phrases at start or after a space
        for phrase in question_phrases:
            if re.search(phrase, clean_text.lower()):
                return True, clean_text, ""
            if re.search(r"\s" + phrase, clean_text.lower()):
                return True, clean_text, ""
        
        # Check for question-like structure without explicit question mark
        question_indicators = [
            r"can you", r"would you", r"could you", r"do you",
            r"tell me", r"describe", r"explain", r"think about",
            r"remember", r"recall", r"imagine", r"share",
            r"what if", r"how about", r"let's talk about"
        ]
        
        for indicator in question_indicators:
            if re.search(rf"\b{indicator}\b", clean_text.lower()):
                return True, clean_text, ""
        
        return False, None, None
    
    def clean_response(self, response):
        """Clean up the response text."""
        if response is None:
            return ""
        if response.startswith('"'):
            response = response[1:]
        if response.endswith('"'):
            response = response[:-1]
        return response.strip()
    
    def handle_interaction(self, child_input, prompt, context_before, context_after, 
                          target_vocab=None, vocab_role=None, special_tag=None, depth=1, 
                          conversation_history=None, remainder_text=None, child_responses=None):
        """Handle different types of interactions with the child."""
        if child_responses is None:
            child_responses = []
        if conversation_history is None:
            conversation_history = []
        
        # Handle empty input
        if not child_input or child_input.strip() == "":
            child_input = "I don't know"

        # --- NEW: Let the LLM answer the child's question dynamically ---
        child_asked_question, child_question, _ = self.contains_question(child_input)
        if child_asked_question and child_question:
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content":
                     "You are Ella, a caring robot. Please answer the child's question "
                     "in one short, happy, encouraging sentence."
                    },
                    {"role": "user", "content": child_question}
                ],
                max_tokens=30,
                temperature=0.8
            )
            quick = self.remove_emojis(resp.choices[0].message.content.strip())
            print(f"Ella: {quick}")
            self.story_log.append(f"Ella: {quick}")

        # Add current response to history
        child_responses.append(child_input)
        conversation_history.append({"role": "user", "content": child_input})
        
        # Special handling for summary tag - randomly choose between three ending types
        if special_tag == "summary":
            # Only choose a new ending type if we haven't chosen one yet
            if not self.chosen_ending_type:
                self.chosen_ending_type = random.choice(["response_summary_closure", "alternative_ending", "story_retelling"])
            
            # Use the appropriate evaluation function based on the chosen ending type
            if self.chosen_ending_type == "story_retelling":
                evaluation = self.scaffolding_selector._evaluate_retelling_complexity_llm(
                    child_input,
                    context_before + context_after)  # give full story
            elif self.chosen_ending_type == "alternative_ending":
                evaluation = self.scaffolding_selector._evaluate_alt_ending_complexity_llm(
                    child_input,
                    context_before + context_after)  # give full story
            else:  # response_summary_closure
                evaluation = self.scaffolding_selector._evaluate_summary_closure_complexity(child_input, context_before)
            
            selected_technique = {
                "name": self.chosen_ending_type,
                "details": self.scaffolding_selector.SCAFFOLDING_TECHNIQUES[self.chosen_ending_type].copy(),
                "support_level": evaluation["support_level"],
                "complexity_score": evaluation["score"]
            }
            example = random.choice(self.scaffolding_selector.SCAFFOLDING_TECHNIQUES[self.chosen_ending_type]["examples"])
            selected_technique["details"]["example"] = example
            
            # Track low complexity responses for story retelling at every depth
            if special_tag == "summary" and selected_technique["name"] == "story_retelling":
                if not hasattr(self, 'low_complexity_count'):
                    self.low_complexity_count = 0
                if evaluation["score"] < 4:
                    self.low_complexity_count += 1
                    print(f"DEBUG: Low complexity count increased to {self.low_complexity_count}")
                else:
                    self.low_complexity_count = 0
                    print(f"DEBUG: Low complexity count reset to 0")
            
            # Prepare special instructions based on the chosen ending type
            if self.chosen_ending_type == "story_retelling":
                special_instructions = """
                SPECIAL INSTRUCTIONS: This is the story retelling section.
                - Ask the child to retell the story in their own words
                - Assess the quality of their retelling
                - Provide appropriate support based on retelling quality
                - Use warm, encouraging language
                - Help fill in gaps if needed
                - Format your response as a question to allow for follow-up interaction
                - DO NOT tell the story yourself - ask the child to tell it
                - Continue the conversation until the child shows high comprehension (score 8-10)
                - If the child shows disinterest (score 0-1) three times in a row, provide a warm closing
                - Generate up to 5 follow-up questions to help the child retell the story
                - Each follow-up should focus on a different aspect of the story
                """
            elif self.chosen_ending_type == "alternative_ending":
                special_instructions = """
                SPECIAL INSTRUCTIONS: This is the alternative ending section.
                - Ask the child to create an alternative ending for the story
                - DO NOT provide an alternative ending yourself
                - Ask the child what they think could have happened instead
                - Encourage creative thinking
                - Help develop ideas if needed
                - Format your response as a question to allow for follow-up interaction
                - Your first question MUST be: "How else could the story have ended?"
                - Generate up to 5 follow-up questions to explore different aspects of the alternative ending
                - Each follow-up should focus on a different element (characters, plot, setting, etc.)
                - After five follow-up questions, provide a warm closing
                """
            else:  # response_summary_closure
                special_instructions = """
                SPECIAL INSTRUCTIONS: This is the summary closure section.
                - Ask the child about their favorite part of the story
                - Encourage reflection on the story's meaning
                - Help them connect the story to their own experiences
                - Use warm, encouraging language
                - Format your response as a question to allow for follow-up interaction
                - Generate up to 5 follow-up questions to explore different aspects of the story
                - Each follow-up question must explore a different part of the child's answer
                - Use the child's previous response to guide the next question
                - Avoid yes/no questions
                - Include one question about the target vocabulary if available
                - Questions should be specific to the story content
                - After five follow-up questions, provide a warm closing
                
                EXAMPLE FOLLOW-UP QUESTIONS:
                - "What made [character's action] so important in the story?"
                - "How do you think [character] felt when [event] happened?"
                - "Why was [vocabulary word] important for solving the problem?"
                - "What would you have done differently if you were [character]?"
                - "How did [event] help the characters learn something new?"
                """
        # Adjust technique selection for maximum depth - use transition
        elif depth >= self.max_interaction_depth and not (special_tag == "summary" and self.chosen_ending_type == "story_retelling"):
            selected_technique = {
                "name": "transition",
                "details": self.scaffolding_selector.SCAFFOLDING_TECHNIQUES["transition"].copy(),
                "support_level": "low",
                "complexity_score": 8
            }
            example = random.choice(self.scaffolding_selector.SCAFFOLDING_TECHNIQUES["transition"]["examples"])
            selected_technique["details"]["example"] = example
            special_instructions = None
        else:
            selected_technique = self.scaffolding_selector.select_technique(
                child_input, prompt, context_before, context_after,
                target_vocab, vocab_role, self.max_interaction_depth, depth
            )
            special_instructions = None
        
        # Generate response with the updated ResponseGenerator that includes vocab target and role
        # Pass context_after only for transition technique or summary tag
        if selected_technique["name"] == "transition" or special_tag == "summary":
            # For transition or summary, pass both contexts
            response = self.response_generator.generate_response(
                child_input, prompt, context_before, context_after, 
                selected_technique, target_vocab, vocab_role, special_instructions
            )
        else:
            # For all other scaffolding techniques, only pass context_before
            response = self.response_generator.generate_response(
                child_input, prompt, context_before, None, 
                selected_technique, target_vocab, vocab_role, special_instructions
            )
        
        # Clean the response to remove any extra quotation marks
        response = self.clean_response(response)
        
        # Apply remainder text only at the highest level or when reaching max depth
        full_response = response
        if remainder_text and (depth == 1 or depth >= self.max_interaction_depth):
            has_q, _, _ = self.contains_question(response)
            if depth >= self.max_interaction_depth or not has_q or special_tag == "summary":
                full_response = f"{response} {remainder_text}"
        
        conversation_history.append({"role": "assistant", "content": full_response})
        
        # Check if response contains a question
        has_question, pre_question, post_question = self.contains_question(response)
        
        # Clean the response parts
        pre_question = self.clean_response(pre_question)
        post_question = self.clean_response(post_question)
        
        # Determine if we should continue the interaction
        should_continue = False
        
        # For all summary interactions, ensure proper depth handling
        if special_tag == "summary":
            # ——— 1. how many turns are allowed for this summary type ———
            summary_max = self.ending_depth_map.get(
                          self.chosen_ending_type, self.ending_max_depth)

            # ——— 2. are we at the final follow-up? ———
            is_final_turn = depth >= summary_max

            # ——— 3. decide whether to continue ———
            should_continue = not is_final_turn

            # ——— 4. make sure NON-final turns contain an invitation ———
            if should_continue:
                has_q, _, _ = self.contains_question(full_response)
                if not has_q:          # no "?" and no question phrases
                    full_response += " What else did you notice in our adventure?"
                    has_question = True
            else:
                # final turn – guarantee it is a closing statement, not a question
                has_question = False
                # Add special instructions for closing message
                if special_instructions:
                    special_instructions += f"""

                    FINAL CLOSING MESSAGE REQUIREMENTS:
                    This is the final turn of the story interaction. You MUST generate a closing message, NOT a question.
                    
                    1. Use the child's name ({self.child_name}) for personalization
                    2. Acknowledge their participation and specific contributions
                    3. Provide a sense of completion and satisfaction
                    4. End with an encouraging, positive goodbye
                    5. Use warm, friendly language
                    6. Include phrases like "see you tomorrow", "until next time", or similar
                    7. Keep it to 2-3 sentences maximum
                    8. NEVER end with a question mark
                    9. Express your enjoyment of the storytelling experience
                    
                    Example closing messages:
                    - "Good job, {self.child_name}! You did such a great job retelling our story! I can't wait to see you tomorrow for another adventure!"
                    - "Thank you for sharing your wonderful ideas with me today, {self.child_name}! You made our story extra special. See you next time!"
                    - "You did such a good job exploring our story today, {self.child_name}! I had so much fun with you. Let's continue our adventure tomorrow!"
                    - "What a fantastic job you did today, {self.child_name}! Your imagination made our story come alive. See you tomorrow for more fun!"
                    - "I loved hearing your creative ideas today, {self.child_name}! You're such a wonderful storyteller. Until our next adventure together!"
                    """
                else:
                    special_instructions = f"""

                    FINAL CLOSING MESSAGE REQUIREMENTS:
                    This is the final turn of the story interaction. You MUST generate a closing message, NOT a question.
                    
                    1. Use the child's name ({self.child_name}) for personalization
                    2. Acknowledge their participation and specific contributions
                    3. Provide a sense of completion and satisfaction
                    4. End with an encouraging, positive goodbye
                    5. Use warm, friendly language
                    6. Include phrases like "see you tomorrow", "until next time", or similar
                    7. Keep it to 2-3 sentences maximum
                    8. NEVER end with a question mark
                    9. Express your enjoyment of the storytelling experience
                    
                    Example closing messages:
                    - "Good job, {self.child_name}! You did such a great job retelling our story! I can't wait to see you tomorrow for another adventure!"
                    - "Thank you for sharing your wonderful ideas with me today, {self.child_name}! You made our story extra special. See you next time!"
                    - "You did such a good job exploring our story today, {self.child_name}! I had so much fun with you. Let's continue our adventure tomorrow!"
                    - "What a fantastic job you did today, {self.child_name}! Your imagination made our story come alive. See you tomorrow for more fun!"
                    - "I loved hearing your creative ideas today, {self.child_name}! You're such a wonderful storyteller. Until our next adventure together!"
                    """

            print(f"DEBUG: summary_closure depth {depth}/{summary_max} | "
                  f"continue={should_continue} | final={is_final_turn}")
        # For regular interactions, follow normal depth limit
        else:
            should_continue = depth < self.max_interaction_depth
        
        # Always print the robot's response
        print(f"Robot: {full_response}")
        
        # Log scaffolding strategy and robot's prompt for all depths
        strategy_log = f"[Scaffolding Strategy: {selected_technique['name']} ({selected_technique['support_level']} support) - Complexity Score: {selected_technique['complexity_score']}/10]"
        if target_vocab:
            vocab_info = f"{target_vocab}"
            if vocab_role:
                vocab_info += f" ({vocab_role})"
            strategy_log += f" [Target Vocabulary: {vocab_info}]"
        if special_tag:
            strategy_log += f" [Special Tag: {special_tag}]"
        self.story_log.append(strategy_log)
        self.story_log.append(f"Robot: {full_response.strip()}")
        
        if should_continue and has_question:
            depth_indicator = ""
            if depth > 1:
                # For story retelling, show just the follow-up number
                if special_tag == "summary" and self.chosen_ending_type == "story_retelling":
                    depth_indicator = f"[Follow-up question {depth}]"
                # For other ending interactions, show progress towards ending_depth_map
                elif special_tag == "summary":
                    max_depth = self.ending_depth_map.get(self.chosen_ending_type, self.ending_max_depth)
                    depth_indicator = f"[Follow-up question {depth}/{max_depth-1}]"
                    if depth == max_depth - 1:
                        depth_indicator += " (Final follow-up)"
                # For regular interactions, show progress towards max_interaction_depth
                else:
                    depth_indicator = f"[Follow-up question {depth}/{self.max_interaction_depth-1}]"
                    if depth == self.max_interaction_depth - 1:
                        depth_indicator += " (Final follow-up)"
            
            follow_up_input = input(f"Child {depth_indicator}: ")
            
            if depth > 1:
                self.story_log.append(f"Child (Follow-up {depth}): {follow_up_input}")
            else:
                self.story_log.append(f"Child: {follow_up_input}")
            
            modified_context_before = context_before + "\n" + "\n".join(
                [f"{'Child' if item['role'] == 'user' else 'Robot'}: {item['content']}" 
                for item in conversation_history[:-1]]
            )
            
            # Include conversation history in the prompt for better context
            conversation_context = "\nPrevious conversation:\n" + "\n".join(
                [f"{item['role'].capitalize()}: {item['content']}" for item in conversation_history]
            )
            
            # Add prior conversation to ground follow-up questions
            if child_responses and len(child_responses) > 0:
                conversation_context += "\nPrevious responses from the child:\n"
                for i, resp in enumerate(child_responses):
                    conversation_context += f"- Turn {i+1}: \"{resp}\"\n"
            
            modified_prompt = prompt + conversation_context
            
            # Don't pass post_question to recursive calls
            follow_up_response, follow_up_technique = self.handle_interaction(
                follow_up_input, 
                modified_prompt,  # Use modified prompt with conversation history
                modified_context_before,
                context_after,
                target_vocab,  # Pass the target vocabulary to recursive calls
                vocab_role,    # Pass the vocabulary role to recursive calls
                special_tag,   # Pass the special tag to recursive calls
                depth + 1,
                conversation_history,
                None,  # Set remainder_text to None for intermediate depths
                child_responses  # Pass the updated child responses
            )
            
            # Only append post_question at the final return (depth=1)
            if depth == 1:
                full_follow_up_response = f"{follow_up_response} {post_question}".strip()
            else:
                full_follow_up_response = follow_up_response
            
            return full_follow_up_response, selected_technique
        else:
            return full_response, selected_technique
    
    def process_story(self):
        print("\n === Starting interactive story session...=== \n")
        
        if self.test_mode:
            print("Running in test mode - skipping to last interaction...")
            # Find the last section with a prompt
            last_section = None
            for section in reversed(self.story_sections):
                if section['prompt']:
                    last_section = section
                    break
            
            if last_section:
                # Use regex to remove all interaction tags completely
                display_text = re.sub(r'<interaction.*?</interaction>', '', last_section['text'])
                
                print(f"Robot:\n{display_text}")
                print(f"{last_section['prompt']}\n")
                self.story_log.append(f"Robot:\n{last_section['text']}")
                
                child_input = input(f"{self.child_name}: ")
                self.story_log.append(f"Child: {child_input}")
                
                # Pass both target vocabulary, vocab role, and special tag to handle_interaction
                ai_response, technique = self.handle_interaction(
                    child_input, last_section['prompt'], last_section['context_before'], 
                    last_section['context_after'], last_section['vocab'], last_section['vocab_role'], last_section['special_tag']
                )
                
                if not self.contains_question(ai_response)[0]:
                    print(f"Robot: {ai_response}")
            else:
                print("No interactive sections found in the story.")
        else:
            # Original process_story logic
            for i, section in enumerate(self.story_sections):
                if section['prompt']:
                    # Use regex to remove all interaction tags completely
                    display_text = re.sub(r'<interaction.*?</interaction>', '', section['text'])
                    
                    print(f"Robot:\n{display_text}")
                    print(f"{section['prompt']}\n")
                    self.story_log.append(f"Robot:\n{section['text']}")
                    
                    child_input = input(f"{self.child_name}: ")
                    self.story_log.append(f"Child: {child_input}")
                    
                    # Pass both target vocabulary, vocab role, and special tag to handle_interaction
                    ai_response, technique = self.handle_interaction(
                        child_input, section['prompt'], section['context_before'], 
                        section['context_after'], section['vocab'], section['vocab_role'], section['special_tag']
                    )
                    
                    if not self.contains_question(ai_response)[0]:
                        print(f"Robot: {ai_response}")
                else:
                    # Also clean any interaction tags from non-prompt sections
                    clean_text = re.sub(r'<interaction.*?</interaction>', '', section['text'])
                    print(f"Robot:\n{clean_text.strip()}\n")
                    self.story_log.append(f"Robot:\n{section['text']}")
        
        return self.story_log

    def save_interaction_log(self, output_file):
        with open(output_file, 'w') as file:
            log_entries = []
            
            for entry in self.story_log:
                # Clean each entry
                cleaned = entry.strip()
                
                # Handle quote removal for log entries
                if cleaned.startswith('Robot: "') and cleaned.endswith('"'):
                    cleaned = f"Robot: {cleaned[8:-1]}"
                elif cleaned.startswith('Child: "') and cleaned.endswith('"'):
                    cleaned = f"Child: {cleaned[8:-1]}"
                    
                if cleaned:  # Skip empty lines
                    log_entries.append(cleaned)
            
            # Join with single newlines and ensure no double spacing
            file.write("\n".join(log_entries))
            print(f"Interaction log saved to {output_file}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python interaction_handler.py  [openai_api_key] [--max-depth N] [--response-length short|standard] [--test-mode]")
        sys.exit(1)
    
    story_file_path = sys.argv[1]
    api_key = None
    max_depth = 3
    response_length = "short"  # Default to short responses
    test_mode = False
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--max-depth" and i+1 < len(sys.argv):
            try:
                max_depth = int(sys.argv[i+1])
                i += 2
            except ValueError:
                print(f"Error: --max-depth requires a number, got '{sys.argv[i+1]}'")
                sys.exit(1)
        elif sys.argv[i] == "--response-length" and i+1 < len(sys.argv):
            if sys.argv[i+1] in ["short", "standard"]:
                response_length = sys.argv[i+1]
                i += 2
            else:
                print(f"Error: --response-length must be 'short' or 'standard', got '{sys.argv[i+1]}'")
                sys.exit(1)
        elif sys.argv[i] == "--test-mode":
            test_mode = True
            i += 1
        elif not api_key:
            api_key = sys.argv[i]
            i += 1
        else:
            i += 1
    
    output_file = os.path.splitext(story_file_path)[0] + "_interaction_log.txt"
    
    try:
        handler = StoryInteractionHandler(story_file_path, api_key, max_depth, response_length, test_mode)
        handler.process_story()
        handler.save_interaction_log(output_file)
        print("\n === Interactive Story Session completed. ===")
    except ValueError as e:
        print(f"Error: {e}")
        print("\nYou can provide your API key directly as an command line argument:")
        print("python interaction_handler.py story_file.txt your_api_key")
        sys.exit(1)

if __name__ == "__main__":
    main()