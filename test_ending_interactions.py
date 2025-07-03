#!/usr/bin/env python3
"""
Test script specifically for ending interactions to verify closing messages work correctly.
"""

import os
import sys
from interaction_handler import StoryInteractionHandler
from response_generator import ResponseGenerator

def test_ending_interactions():
    """Test the ending interactions to ensure they generate proper closing messages."""
    
    # Test API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        return
    
    print("=== Testing Ending Interactions ===\n")
    
    # Create a simple test story with ending interaction
    test_story = """
Once upon a time, there was a magical garden where flowers could talk and butterflies could sing.

<interaction vocab="garden" role="setting">What do you think the garden looked like?</interaction>

The garden was filled with colorful flowers and friendly animals.

<interaction vocab="flowers" role="characters">What colors were the flowers?</interaction>

The flowers were red, blue, and yellow, and they all lived happily together.

<interaction vocab="happily" role="emotion">How do you think the flowers felt?</interaction>

And they all lived happily ever after.

<interaction vocab="summary" role="summary">What was your favorite part of the story?</interaction>
"""
    
    # Write test story to file
    with open("test_ending_story.txt", "w") as f:
        f.write(test_story)
    
    try:
        # Create interaction handler
        handler = StoryInteractionHandler("test_ending_story.txt", api_key, max_interaction_depth=5, test_mode=True)
        
        print("Test story created with ending interaction.")
        print("The system should now test the ending interaction and generate a closing message.\n")
        
        # Process the story (this will trigger the ending interaction)
        handler.process_story()
        
        print("\n=== Test completed ===")
        print("Check the generated interaction log to see if the ending interaction produced a proper closing message.")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test file
        if os.path.exists("test_ending_story.txt"):
            os.remove("test_ending_story.txt")

if __name__ == "__main__":
    test_ending_interactions() 