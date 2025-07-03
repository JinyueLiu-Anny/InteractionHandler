#!/usr/bin/env python3
"""
Direct test of ending interaction logic without pre-story interaction.
"""

import os
import sys
from response_generator import ResponseGenerator

def test_ending_closing_message():
    """Test the ending interaction closing message generation directly."""
    
    # Test API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    print("=== Direct Test of Ending Interaction Closing Message ===\n")
    
    # Create response generator
    generator = ResponseGenerator(api_key)
    
    # Test parameters
    child_input = "I liked when the flowers were happy"
    prompt = "What was your favorite part of the story?"
    context_before = "The flowers were red, blue, and yellow, and they all lived happily together."
    context_after = "And they all lived happily ever after."
    
    # Test the three ending types
    ending_types = [
        {
            "name": "story_retelling",
            "support_level": "medium",
            "complexity_score": 5
        },
        {
            "name": "alternative_ending", 
            "support_level": "medium",
            "complexity_score": 4
        },
        {
            "name": "response_summary_closure",
            "support_level": "low", 
            "complexity_score": 6
        }
    ]
    
    for ending_type in ending_types:
        print(f"\n--- Testing {ending_type['name']} closing message ---")
        
        # Special instructions for final closing message
        special_instructions = f"""

        FINAL CLOSING MESSAGE REQUIREMENTS:
        This is the final turn of the story interaction. You MUST generate a closing message, NOT a question.
        
        1. Use the child's name (Caro) for personalization
        2. Acknowledge their participation and specific contributions
        3. Provide a sense of completion and satisfaction
        4. End with an encouraging, positive goodbye
        5. Use warm, friendly language
        6. Include phrases like "see you tomorrow", "until next time", or similar
        7. Keep it to 2-3 sentences maximum
        8. NEVER end with a question mark
        9. Express your enjoyment of the storytelling experience
        
        Example closing messages:
        - "Good job, Caro! You did such a great job retelling our story! I can't wait to see you tomorrow for another adventure!"
        - "Thank you for sharing your wonderful ideas with me today, Caro! You made our story extra special. See you next time!"
        - "You did such a good job exploring our story today, Caro! I had so much fun with you. Let's continue our adventure tomorrow!"
        - "What a fantastic job you did today, Caro! Your imagination made our story come alive. See you tomorrow for more fun!"
        - "I loved hearing your creative ideas today, Caro! You're such a wonderful storyteller. Until our next adventure together!"
        """
        
        try:
            # Generate response
            response = generator.generate_response(
                child_input, prompt, context_before, context_after,
                ending_type, target_vocab="happily", vocab_role="emotion", 
                special_instructions=special_instructions
            )
            
            print(f"Generated response: {response}")
            print(f"Ends with question mark: {response.strip().endswith('?')}")
            print(f"Contains closing phrase: {'see you' in response.lower() or 'tomorrow' in response.lower() or 'next time' in response.lower()}")
            
        except Exception as e:
            print(f"Error generating response for {ending_type['name']}: {e}")

if __name__ == "__main__":
    test_ending_closing_message() 