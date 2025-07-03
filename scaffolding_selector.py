import random
import re
import json
import os
import sys
from typing import Dict, List, Optional, Any

import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ScaffoldingSelector:
    """Selects appropriate scaffolding techniques based on child input and context."""
    
    def __init__(self, use_llm: bool = True, api_key: Optional[str] = None):
        """Initialize the scaffolding selector.
        
        Args:
            use_llm: Whether to use the LLM for technique selection
            api_key: OpenAI API key (optional if set in environment)
        """
        # Track previously used techniques to avoid repetition
        self.previously_used: List[str] = []
        self.use_llm = use_llm
        
        # Load scaffolding techniques from JSON file
        self.SCAFFOLDING_TECHNIQUES = self._load_scaffolding_techniques()
        
        # Load the system and user prompts
        self.system_prompt = self._load_text_file('prompts/scaffolding_system_prompt.txt')
        self.user_prompt_template = self._load_text_file('prompts/scaffolding_user_prompt.txt')
        
        # Set up OpenAI client if using LLM
        if self.use_llm:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OpenAI API key is missing! Please provide it as an argument or in .env file.")
            self.client = openai.OpenAI(api_key=self.api_key)
    
    def _load_text_file(self, filepath: str) -> str:
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
            print(f"ERROR: Could not find '{filepath}'")
            print("Make sure the prompts directory exists and contains the required files.")
            sys.exit(1)
    
    def _load_scaffolding_techniques(self) -> Dict[str, Dict[str, Any]]:
        """Load scaffolding techniques from JSON file.
        
        Returns:
            Dictionary containing scaffolding techniques
        """
        try:
            with open('prompts/scaffolding_techniques.json', 'r') as file:
                techniques = json.load(file)
                
            # Add the new ending techniques
            techniques.update({
                "story_retelling": {
                    "full_definition": "Assesses the child's comprehension and memory of the story through retelling",
                    "support_level": "low",
                    "examples": [
                        "Can you tell me what happened in the story?",
                        "What do you remember about Sparky's adventure?",
                        "Tell me about what happened with Sparky and the butterfly"
                    ]
                },
                "alternative_ending": {
                    "full_definition": "Encourages creative thinking by asking for a different story ending",
                    "support_level": "low",
                    "examples": [
                        "How else could the story have ended?",
                        "What if Sparky and the butterfly had done something different?",
                        "Can you think of another way the story could have ended?"
                    ]
                },
                "response_summary_closure": {
                    "full_definition": "Helps children reflect on and summarize their understanding of the story through story-specific questions.",
                    "support_level": "low",
                    "examples": [
                        "What was the most exciting part of the story for you?",
                        "How did the characters solve their problem in the story?",
                        "What would you have done if you were in the story?",
                        "What lesson did we learn from the story?",
                        "How did the story make you feel and why?",
                        "What was the biggest challenge in the story?",
                        "How did the characters help each other?",
                        "What would you tell a friend about this story?"
                    ]
                }
            })
            return techniques
        except FileNotFoundError:
            print("ERROR: Could not find 'prompts/scaffolding_techniques.json'")
            print("Make sure the prompts directory exists and contains the required files.")
            sys.exit(1)
        except json.JSONDecodeError:
            print("ERROR: Invalid JSON in 'prompts/scaffolding_techniques.json'")
            print("The file exists but contains invalid JSON. Please check the file format.")
            sys.exit(1)
    
    def _evaluate_retelling_complexity(self, response: str, context_before: str) -> Dict[str, Any]:
        """Evaluate the complexity of a story retelling response.
        
        Args:
            response: The child's retelling response
            context_before: The story context for reference
            
        Returns:
            Dictionary containing score, support level, and scoring rationale
        """
        # Initialize scoring components
        sequence_accuracy = 0
        key_event_recall = 0
        character_involvement = 0
        vocabulary_usage = 0
        plot_coherence = 0
        detail_enrichment = 0
        
        # Check for basic response quality
        if not response or len(response.strip()) < 5:
            return {
                "score": 1,
                "support_level": "high",
                "rationale": {
                    "sequence_accuracy": 0,
                    "key_event_recall": 0,
                    "character_involvement": 0,
                    "vocabulary_usage": 0,
                    "plot_coherence": 0,
                    "detail_enrichment": 0
                }
            }
        
        # Check for memory/recall issues
        if any(phrase in response.lower() for phrase in ["don't remember", "don't know", "forgot", "can't remember"]):
            return {
                "score": 2,
                "support_level": "high",
                "rationale": {
                    "sequence_accuracy": 0,
                    "key_event_recall": 0,
                    "character_involvement": 1,
                    "vocabulary_usage": 0,
                    "plot_coherence": 0,
                    "detail_enrichment": 1
                }
            }
        
        # Evaluate sequence accuracy
        if "sparky" in response.lower() and "butterfly" in response.lower():
            sequence_accuracy += 2
        elif "sparky" in response.lower() or "butterfly" in response.lower():
            sequence_accuracy += 1
        
        # Evaluate key event recall
        key_events = ["box", "garden", "friends", "play", "happy"]
        for event in key_events:
            if event in response.lower():
                key_event_recall += 1
                if key_event_recall >= 3:
                    break
        
        # Evaluate character involvement
        if "sparky" in response.lower() and "butterfly" in response.lower():
            character_involvement += 2
        elif "sparky" in response.lower() or "butterfly" in response.lower():
            character_involvement += 1
        
        # Evaluate vocabulary usage
        target_vocab = ["explore", "butterfly", "happy", "friends"]
        for word in target_vocab:
            if word in response.lower():
                vocabulary_usage += 1
                if vocabulary_usage >= 2:
                    break
        
        # Evaluate plot coherence
        if len(response.split()) > 10 and any(word in response.lower() for word in ["because", "then", "so", "and"]):
            plot_coherence += 2
        elif len(response.split()) > 5:
            plot_coherence += 1
        
        # Evaluate detail and enrichment
        if len(response.split()) > 15 or any(word in response.lower() for word in ["beautiful", "colorful", "wonderful", "fun"]):
            detail_enrichment += 1
        
        # Calculate total score
        total_score = (
            sequence_accuracy +
            key_event_recall +
            character_involvement +
            vocabulary_usage +
            plot_coherence +
            detail_enrichment
        )
        
        # Determine support level
        if total_score <= 3:
            support_level = "high"
        elif total_score <= 6:
            support_level = "medium"
        else:
            support_level = "low"
        
        return {
            "score": total_score,
            "support_level": support_level,
            "rationale": {
                "sequence_accuracy": sequence_accuracy,
                "key_event_recall": key_event_recall,
                "character_involvement": character_involvement,
                "vocabulary_usage": vocabulary_usage,
                "plot_coherence": plot_coherence,
                "detail_enrichment": detail_enrichment
            }
        }
    
    def _evaluate_summary_closure_complexity(self, response, context):
        """Evaluate complexity of response summary closure responses."""
        prompt = f"""Evaluate the child's response to a summary closure question about the story.
        Story context: {context}
        Child's response: {response}
        
        Evaluate based on these criteria:
        1. Reflection Quality (0-2 points):
           - Deep reflection on story meaning
           - Personal connection to story
           - Emotional engagement
        
        2. Story Understanding (0-2 points):
           - Comprehension of key events
           - Understanding of story themes
           - Connection to story elements
        
        3. Language Use (0-2 points):
           - Appropriate vocabulary
           - Clear expression
           - Age-appropriate language
        
        4. Engagement Level (0-2 points):
           - Enthusiasm in response
           - Willingness to share
           - Interest in discussion
        
        5. Critical Thinking (0-2 points):
           - Analysis of story elements
           - Evaluation of story impact
           - Insightful observations
        
        Return a JSON object with:
        - score: total points (0-10)
        - support_level: "high" (0-3), "medium" (4-6), or "low" (7-10)
        - rationale: brief explanation of scoring
        """
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that evaluates children's responses to story summary questions. Always respond with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            # Extract JSON from the response (in case there's any extra text)
            response_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            result = json.loads(response_text)
            
            # Validate the result has required fields
            if not all(key in result for key in ["score", "support_level", "rationale"]):
                raise ValueError("Missing required fields in evaluation result")
            
            # Ensure score is within valid range
            result["score"] = max(0, min(10, float(result["score"])))
            
            # Ensure support level is valid
            if result["support_level"] not in ["high", "medium", "low"]:
                result["support_level"] = "medium"
            
            return result
            
        except Exception as e:
            print(f"Error evaluating summary closure complexity: {str(e)}")
            # Return a default evaluation for error cases
            return {
                "score": 5,
                "support_level": "medium",
                "rationale": "Error in evaluation, defaulting to medium support"
            }
    
    def select_technique(self, child_input, prompt, context_before, context_after, 
                        target_vocab=None, vocab_role=None, max_depth=3, depth=1):
        """
        Select an appropriate scaffolding technique based on the child's response.
        
        Args:
            child_input: The child's response
            prompt: The question or prompt given to the child
            context_before: Story context preceding this interaction
            context_after: Story context following this interaction
            target_vocab: Optional target vocabulary word
            vocab_role: Optional role of the vocabulary word (new, easy, review)
            max_depth: Maximum depth of follow-up questions
            depth: Current depth of the interaction
            
        Returns:
            Dictionary containing the selected technique and its details
        """
        # Check for disengaged or empty responses with improved detection
        def is_disengaged_input(input_text):
            if not input_text or not input_text.strip():
                return True
                
            # List of explicit disengagement phrases
            disengaged_phrases = [
                "i don't know", "idk", "dunno", "no idea",
                "i forgot", "i can't remember", "not sure",
                "i don't remember", "i don't recall"
            ]
            
            # Clean and lowercase the input
            clean_input = input_text.strip().lower()
            
            # Check for explicit disengagement phrases
            if any(phrase in clean_input for phrase in disengaged_phrases):
                return True
                
            # Check for very short responses that aren't meaningful
            words = clean_input.split()
            if len(words) <= 1 and clean_input not in ["yes", "no", "both", "maybe", "okay", "sure"]:
                return True
                
            return False

        # Use the improved disengagement detection
        if is_disengaged_input(child_input):
            print(f"DEBUG: Detected disengaged input: '{child_input}'")
            # For disengaged responses, use high support techniques
            high_support_techniques = ["reducing_choices", "co-participating", "eliciting"]
            selected_technique = random.choice(high_support_techniques)
            return {
                "name": selected_technique,
                "details": self.SCAFFOLDING_TECHNIQUES[selected_technique].copy(),
                "support_level": "high",
                "complexity_score": 0
            }
        
        # If we're at max depth, use transition technique to close the conversation
        if depth >= max_depth:
            return self._select_transition_technique()
        
        # If LLM is not enabled, we still need a basic selection method
        if not self.use_llm:
            print("WARNING: LLM-based technique selection is disabled.")
            complexity_score = 3 if len(child_input.split()) < 7 else 6
            support_level = "high" if complexity_score < 5 else "low"
            return self._select_technique_randomly(support_level, complexity_score)
        
        # If child input is empty, handle this case explicitly
        if not child_input or child_input.strip() == "":
            print("WARNING: Empty child input received. Using high support technique.")
            return self._select_technique_randomly("high", 2)
            
        # Get available techniques by support level for the prompt
        high_support_techniques = self._get_available_techniques("high")
        low_support_techniques = self._get_available_techniques("low")
        
        # Prepare technique information for the prompt
        high_support_info = self._format_techniques_for_prompt(high_support_techniques)
        low_support_info = self._format_techniques_for_prompt(low_support_techniques)
        
        # Format the user prompt using the template from the file
        user_prompt = self.user_prompt_template.format(
            prompt=prompt,
            child_input=child_input,
            context_before=context_before,
            context_after=context_after,
            target_vocab=target_vocab or "None provided",
            vocab_role=vocab_role or "Not specified",
            high_support_info=high_support_info,
            low_support_info=low_support_info
        )
        
        # Make the API call to get technique recommendation
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=150,
                temperature=0.2
            )
            
            # Parse the JSON response
            response_text = response.choices[0].message.content.strip()
            selection_result = self._parse_llm_response(response_text, child_input)
            
            return selection_result
            
        except Exception as e:
            # Report error instead of using fallback
            print(f"ERROR in LLM API call: {e}")
            print("Failed to select a scaffolding technique using the LLM.")
            raise
    
    def _select_transition_technique(self) -> Dict[str, Any]:
        """Select the transition technique to close an interaction.
        
        Returns:
            Dictionary with transition technique details
        """
        # Get transition technique details
        technique_details = self.SCAFFOLDING_TECHNIQUES["transition"].copy()
        
        # Get a random example from the transition technique
        technique_examples = self.SCAFFOLDING_TECHNIQUES["transition"]["examples"]
        selected_example = random.choice(technique_examples)
        
        # Add the selected example to the details
        technique_details["example"] = selected_example
        
        # Return the transition technique with its details
        return {
            "name": "transition",
            "details": technique_details,
            "support_level": "low",
            "complexity_score": 8
        }
    
    def _parse_llm_response(self, response_text: str, child_input: str) -> Dict[str, Any]:
        """Parse the LLM response and extract technique selection.
        
        Args:
            response_text: The raw text response from the LLM
            child_input: The child's input (used for error reporting)
            
        Returns:
            Dictionary with selected technique details
        """
        try:
            # Extract JSON from the response (in case there's any extra text)
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(0)
            
            result = json.loads(response_text)
            
            # Extract the values
            complexity_score = float(result.get("complexity_score", 5))
            support_level = result.get("support_level", "low")
            selected_technique_name = result.get("selected_technique", "")
            
            # Validate support level
            if support_level not in ["high", "low"]:
                print(f"ERROR: Invalid support level '{support_level}' in LLM response.")
                print(f"Raw response: {response_text}")
                raise ValueError(f"Invalid support level: {support_level}")
            
            # Validate selected technique
            available_techniques = self._filter_techniques_by_support(support_level)
            # Remove "transition" from available techniques for normal selection
            if "transition" in available_techniques:
                available_techniques.pop("transition")
                
            if selected_technique_name not in available_techniques:
                print(f"ERROR: Invalid technique name '{selected_technique_name}' in LLM response.")
                print(f"Raw response: {response_text}")
                print(f"Available techniques: {list(available_techniques.keys())}")
                raise ValueError(f"Invalid technique name: {selected_technique_name}")
            
            # Update previously used techniques
            self._update_previously_used(selected_technique_name)
            
            # Get a random example from the selected technique
            technique_examples = self.SCAFFOLDING_TECHNIQUES[selected_technique_name]["examples"]
            selected_example = random.choice(technique_examples)
            
            # Create a copy of the technique details with the selected example
            technique_details = self.SCAFFOLDING_TECHNIQUES[selected_technique_name].copy()
            technique_details["example"] = selected_example
            
            # Return the selected technique with its details
            return {
                "name": selected_technique_name,
                "details": technique_details,
                "support_level": support_level,
                "complexity_score": complexity_score
            }
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Report error details without fallback
            print(f"ERROR parsing LLM response: {e}")
            print(f"Child input: '{child_input}'")
            print(f"Raw LLM response: '{response_text}'")
            raise
    
    def _update_previously_used(self, technique_name: str) -> None:
        """Update the list of previously used techniques.
        
        Args:
            technique_name: The name of the technique to add
        """
        self.previously_used.append(technique_name)
        # Keep only the last 2 techniques
        if len(self.previously_used) > 2:
            self.previously_used.pop(0)
    
    def _format_techniques_for_prompt(self, techniques: Dict[str, Dict[str, Any]]) -> str:
        """Format technique information for the prompt.
        
        Args:
            techniques: Dictionary of techniques to format
            
        Returns:
            Formatted string of techniques for the prompt
        """
        formatted_info = ""
        for name, details in techniques.items():
            # Exclude the "transition" strategy from normal selection
            if name != "transition":
                formatted_info += f"- {name}: {details['full_definition']}\n"
        return formatted_info
    
    def _get_available_techniques(self, support_level: str) -> Dict[str, Dict[str, Any]]:
        """Get available techniques for a support level, prioritizing unused ones.
        
        Args:
            support_level: "high" or "low" support level
            
        Returns:
            Dictionary of available techniques
        """
        all_techniques = self._filter_techniques_by_support(support_level)
        
        # Remove the "transition" strategy from normal selection
        if "transition" in all_techniques:
            all_techniques = {name: details for name, details in all_techniques.items() if name != "transition"}
        
        # Prioritize techniques that haven't been used recently
        prioritized_techniques = {name: details for name, details in all_techniques.items() 
                                 if name not in self.previously_used}
        
        # If all techniques have been used, reset and use all available
        if not prioritized_techniques:
            prioritized_techniques = all_techniques
        
        return prioritized_techniques
    
    def _filter_techniques_by_support(self, support_level: str) -> Dict[str, Dict[str, Any]]:
        """Filter scaffolding techniques based on the required support level.
        
        Args:
            support_level: "high" or "low" support level
            
        Returns:
            Dictionary of filtered techniques
        """
        return {name: details for name, details in self.SCAFFOLDING_TECHNIQUES.items() 
                if details["support_level"] == support_level}
    
    def _select_technique_randomly(self, support_level: str, complexity_score: float) -> Dict[str, Any]:
        """Select a technique randomly based on support level.
        Used only when LLM is disabled or as a minimal fallback for empty input.
        
        Args:
            support_level: "high" or "low" support level
            complexity_score: The calculated complexity score
            
        Returns:
            Dictionary with selected technique details
        """
        # Get appropriate techniques for this support level
        available_techniques = self._filter_techniques_by_support(support_level)
        
        # Remove the "transition" strategy from normal selection
        if "transition" in available_techniques:
            available_techniques = {name: details for name, details in available_techniques.items() if name != "transition"}
        
        if not available_techniques:
            print(f"ERROR: No available techniques found for support level: {support_level}")
            raise ValueError(f"No techniques available for support level: {support_level}")
        
        # Add some randomization to avoid repetition
        technique_names = list(available_techniques.keys())
        
        # Prioritize techniques that haven't been used recently
        unused_techniques = [t for t in technique_names if t not in self.previously_used]
        
        if unused_techniques:
            selected_technique_name = random.choice(unused_techniques)
        else:
            # If all have been used, just pick randomly
            selected_technique_name = random.choice(technique_names)
            # And reset the previously used list
            self.previously_used = []
        
        # Update previously used techniques
        self._update_previously_used(selected_technique_name)
        
        # Get a random example from the selected technique
        technique_examples = self.SCAFFOLDING_TECHNIQUES[selected_technique_name]["examples"]
        selected_example = random.choice(technique_examples)
        
        # Create a copy of the technique details with the selected example
        technique_details = self.SCAFFOLDING_TECHNIQUES[selected_technique_name].copy()
        technique_details["example"] = selected_example
        
        # Return the selected technique with its details
        return {
            "name": selected_technique_name,
            "details": technique_details,
            "support_level": support_level,
            "complexity_score": complexity_score
        }
    
    def get_technique_info(self) -> Dict[str, Dict[str, Any]]:
        """Return information about all available scaffolding techniques.
        
        Returns:
            Dictionary of all scaffolding techniques
        """
        return self.SCAFFOLDING_TECHNIQUES

    def _evaluate_retelling_complexity_llm(self, response:str, context:str)->Dict[str,Any]:
        """
        Evaluate story retelling complexity using LLM-based rubric.
        
        Args:
            response: Child's retelling response
            context: Full story context
            
        Returns:
            Dict containing score, support_level, and rationale
        """
        prompt = self._load_text_file("prompts/retelling_user_prompt.txt").format(
                    context=context, response=response)
        try:
            llm = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system",
                     "content": self._load_text_file("prompts/retelling_system_prompt.txt")},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=150)

            # pull the JSON safely
            text = llm.choices[0].message.content.strip()
            js = json.loads(re.search(r"\{.*\}", text, re.DOTALL).group(0))

            # sanitise
            js["score"] = max(0, min(10, int(js["score"])))
            if js["score"]<=3: js["support_level"]="high"
            elif js["score"]<=6: js["support_level"]="medium"
            else: js["support_level"]="low"
            return js
        except Exception as e:
            print("LLM retelling evaluation failed:", e)
            return {"score":5, "support_level":"medium",
                    "rationale":["fallback"]*5}

    def _evaluate_alt_ending_complexity_llm(self, response:str, context:str):
        """
        Evaluate alternative ending complexity using LLM-based rubric.
        
        Args:
            response: Child's alternative ending response
            context: Full story context
            
        Returns:
            Dict containing score, support_level, and rationale
        """
        prompt = (self._load_text_file(
                    "prompts/altending_user_prompt.txt")
                  .format(context=context, response=response))
        try:
            out = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                   {"role":"system",
                    "content": self._load_text_file(
                               "prompts/altending_system_prompt.txt")},
                   {"role":"user", "content": prompt}],
                temperature=0.1, max_tokens=150)

            # Extract JSON with better error handling
            response_text = out.choices[0].message.content.strip()
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if not json_match:
                print("Warning: Could not find JSON in LLM response:", response_text)
                return {
                    "score": 5,
                    "support_level": "medium",
                    "rationale": ["fallback"] * 5
                }
            
            js = json.loads(json_match.group(0))
            
            # Validate and normalize the response
            js["score"] = max(0, min(10, int(js.get("score", 5))))
            
            # Normalize support level based on score
            if js["score"] <= 3:
                js["support_level"] = "high"
            elif js["score"] <= 6:
                js["support_level"] = "medium"
            else:
                js["support_level"] = "low"
                
            return js
            
        except Exception as e:
            print(f"Alt-ending LLM eval failed: {str(e)}")
            print(f"Response text: {response_text if 'response_text' in locals() else 'No response'}")
            return {
                "score": 5,
                "support_level": "medium",
                "rationale": ["fallback"] * 5
            }