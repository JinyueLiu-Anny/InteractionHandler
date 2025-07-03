import openai
import os
from dotenv import load_dotenv

# Try to load from .env file first
load_dotenv()

class ResponseGenerator:
    """Class to generate responses using selected scaffolding techniques with tailored prompts."""
    
    def __init__(self, api_key=None, response_length="short"):
        """Initialize the response generator with OpenAI API.
        
        Args:
            api_key: OpenAI API key (optional if set in environment)
            response_length: Controls verbosity - 'short' (1-2 sentences) or 'standard' (original behavior)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.response_length = response_length
        
        # Ensure the API key is loaded
        if not self.api_key:
            raise ValueError("OpenAI API key is missing! Please provide it as an argument or in .env file.")
        
        # Set up OpenAI client
        self.client = openai.OpenAI(api_key=self.api_key)
        
        # Define common guidelines and technique-specific system prompts
        self.common_guidelines = self._load_text_file("prompts/response_common_guidelines.txt")
        self.transition_guidelines = self._load_text_file("prompts/response_transition.txt")
        self.summary_closure_guidelines = self._load_text_file("prompts/response_summary_closure.txt")
        self.default_guidelines = self._load_text_file("prompts/response_default.txt")
        self._init_technique_prompts()
    
    def _load_text_file(self, filepath):
        """Load text content from a file.
        
        Args:
            filepath: Path to the text file
            
        Returns:
            String content of the file
        """
        try:
            with open(filepath, 'r') as file:
                return file.read()
        except FileNotFoundError:
            print(f"Warning: Could not find {filepath}. Using default empty string.")
            return ""
    
    def _init_technique_prompts(self):
        """Initialize the technique-specific system prompts by load from files."""
        
        # Initialize technique_prompts dictionary
        self.technique_prompts = {}
        
        # Define the scaffolding techniques to load
        techniques = [
            "co-participating",
            "reducing_choices", 
            "eliciting", 
            "generalizing", 
            "reasoning", 
            "predicting",
            "story_retelling",
            "alternative_ending"
        ]
        
        # Load each technique prompt from its file
        for technique in techniques:
            prompt_path = f"prompts/response_{technique}.txt"
            prompt_content = self._load_text_file(prompt_path)
            
            # Add the common guidelines to each technique prompt
            self.technique_prompts[technique] = f"{prompt_content}\n\n{self.common_guidelines}"
    
    def generate_response(self, child_input, prompt, context_before, context_after, 
                         selected_technique, target_vocab=None, vocab_role=None, special_instructions=None):
        """
        Generate a response based on the child's input and selected technique.
        """
        # Extract conversation history from the prompt if it exists
        conversation_history = ""
        if "Previous conversation:" in prompt:
            parts = prompt.split("Previous conversation:")
            base_prompt = parts[0].strip()
            conversation_history = "Previous conversation:" + parts[1]
        else:
            base_prompt = prompt

        # Extract child's previous responses if they exist
        child_responses = ""
        if "Previous responses from the child:" in conversation_history:
            parts = conversation_history.split("Previous responses from the child:")
            conversation_history = parts[0].strip()
            child_responses = "Previous responses from the child:" + parts[1]

        # Determine the appropriate context section
        if selected_technique["name"] == "transition":
            context_section = f"""
            Story content before the current interaction:
            {context_before}

            Story content after the current interaction:
            {context_after}
            """
        else:
            context_section = f"""
            Story content before the current interaction:
            {context_before}
            """

        # Add vocabulary information if available
        vocab_section = ""
        if target_vocab:
            vocab_section = f"""
            Target vocabulary word: {target_vocab}
            Vocabulary role: {vocab_role}
            """
        
        # Add special instructions if provided
        special_section = ""
        if special_instructions:
            special_section = f"""
            {special_instructions}
            """
            
            # Add adaptive support based on the child's response
            if "summary" in str(special_instructions).lower():
                if len(child_input.split()) <= 3:
                    special_section += """
                    IMPORTANT: The child's response was brief. Provide more scaffolding by:
                    1. Referencing a specific story element they might remember
                    2. Offering two simple options to choose from
                    3. Using a yes/no question followed by a "what if" suggestion
                    """
                elif "don't know" in child_input.lower() or "not sure" in child_input.lower():
                    special_section += """
                    IMPORTANT: The child seems unsure. Help them by:
                    1. Reminding them of a key story moment
                    2. Asking about a specific character's feelings
                    3. Suggesting two possible interpretations
                    4. NEVER repeat the same question
                    5. ALWAYS end with a new, easier question
                    """
            
            # Add specific support for alternative endings
            if "alternative_ending" in str(special_instructions).lower():
                if len(child_input.split()) <= 3 or "don't know" in child_input.lower():
                    special_section += """
                    IMPORTANT: The child needs help imagining an alternative ending. Provide support by:
                    1. Referencing a story element they understood well
                    2. Offering two creative possibilities as examples
                    3. Using a yes/no question followed by a "what if" suggestion
                    4. NEVER repeat the same question
                    5. ALWAYS end with a new, easier question
                    
                    Example prompts:
                    - "What if [character] had a magical helper like a butterfly?"
                    - "Do you think [character] could have used [story element] differently?"
                    - "Imagine if [character] had found a secret path. What might have happened?"
                    """
            
            # Add specific support for story retelling
            if "story_retelling" in str(special_instructions).lower():
                if len(child_input.split()) <= 3 or "don't know" in child_input.lower():
                    special_section += """
                    IMPORTANT: The child needs help retelling the story. Provide support by:
                    1. Reminding them of a key story moment they might remember
                    2. Asking about a specific character's actions or feelings
                    3. Offering two possible story elements to focus on
                    4. NEVER repeat the same question
                    5. ALWAYS end with a new, easier question
                    
                    Example prompts:
                    - "Do you remember when [character] [action]? What happened next?"
                    - "What was [character] feeling when [event] happened?"
                    - "Can you tell me about the part where [event]?"
                    """

        # Construct the user prompt with all context
        user_prompt = f"""
        {context_section}

        {vocab_section}

        {special_section}

        {conversation_history}

        {child_responses}

        Child's response to the question "{base_prompt}":
        "{child_input}"

        Based on the child's response and the conversation history, generate a follow-up question that:
        1. Builds upon their previous responses
        2. Explores a different aspect of the story
        3. Uses warm, encouraging language
        4. Avoids repeating previous questions
        5. Maintains engagement and interest
        6. Provides appropriate scaffolding based on their response length and confidence
        7. Always connects back to specific story elements
        8. Uses the child's own words when possible
        9. NEVER ends with a statement - ALWAYS end with a question
        10. If the child seems unsure, offer simpler options or hints

        Your response should be a single question that continues the conversation naturally.
        """

        # Add strong question formatting requirement for summary interactions
        if selected_technique["name"] in ["response_summary_closure", "alternative_ending", "story_retelling"]:
            # Check if this is the final closing message
            is_final_closing = "FINAL CLOSING MESSAGE REQUIREMENTS" in str(special_instructions)
            
            if is_final_closing:
                user_prompt += """

                CRITICAL FINAL CLOSING REQUIREMENTS:
                1. Your response MUST NOT end with a question mark (?)
                2. Your response MUST be a closing statement, not a question
                3. Use warm, encouraging language
                4. Include the child's name for personalization
                5. Acknowledge their participation and contributions
                6. End with a positive goodbye like "see you tomorrow" or "until next time"
                7. Keep it to 2-3 sentences maximum
                8. Express your enjoyment of the storytelling experience
                9. Provide a sense of completion and satisfaction
                10. NEVER ask a question - this is the final closing message
                """
            else:
                user_prompt += """

                CRITICAL REQUIREMENTS:
                1. Your response MUST end with a question mark (?)
                2. Your response MUST be a question
                3. Do not use statements or summaries
                4. Keep the conversation going with an engaging question
                5. Format: [Your question here?]
                6. If the child seems unsure, offer two simple options
                7. If the child is engaged, ask about a different story element
                8. Always reference specific story details
                9. NEVER repeat the same question
                10. If the child seems stuck, provide a hint or example
                """

        # Select appropriate system prompt based on technique
        if selected_technique["name"] == "transition":
            system_prompt = self.transition_guidelines
        elif "summary" in str(special_instructions).lower():
            system_prompt = self.summary_closure_guidelines
        else:
            # Use technique-specific prompt or default
            system_prompt = self.technique_prompts.get(
                selected_technique["name"], 
                self.default_guidelines
            )

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            response = response.choices[0].message.content.strip()
            
            # Debug logging for response analysis
            print(f"[DEBUG] Final robot response: {response}")
            print(f"[DEBUG] Ends with question: {response.strip().endswith('?')}")
            
            # Check if this is a final closing message
            is_final_closing = "FINAL CLOSING MESSAGE REQUIREMENTS" in str(special_instructions)
            
            # Enforce question ending for story retelling (but not for final closing)
            if selected_technique["name"] == "story_retelling" and not response.strip().endswith("?") and not is_final_closing:
                print("[DEBUG] Story retelling response missing question mark. Adding follow-up question.")
                # Add a contextually appropriate follow-up question
                if "remember" in response.lower():
                    response += " What else do you remember from the story?"
                elif "think" in response.lower():
                    response += " Can you tell me more about that?"
                else:
                    response += " What happened next in the story?"
            
            # For final closing messages, ensure it doesn't end with a question
            if is_final_closing and response.strip().endswith("?"):
                print("[DEBUG] Final closing message ended with question mark. Converting to statement.")
                # Remove the question mark and make it a statement
                response = response.strip().rstrip("?") + "."
                # Add a closing phrase if it doesn't have one
                if not any(phrase in response.lower() for phrase in ["see you", "until next", "tomorrow", "goodbye"]):
                    response += " See you tomorrow for another adventure!"
            
            return response
        except Exception as e:
            print(f"Error generating response: {e}")
            return "That's interesting! Can you tell me more about that?"