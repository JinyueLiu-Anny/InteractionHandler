import os
import random
from interaction_handler import StoryInteractionHandler

def select_random_vocab():
    """Select random vocabulary words from the sets."""
    # Try to load from vocab_sets.txt first
    vocab_sets_path = "storyGenerator-main 2/vocab_sets.txt"
    if os.path.exists(vocab_sets_path):
        with open(vocab_sets_path, 'r') as file:
            vocab_sets = [line.strip().split() for line in file if line.strip()]
            if vocab_sets:
                return random.choice(vocab_sets)
    
    # Fallback to some predefined sets if file not found
    fallback_sets = [
        ["ant", "alligator", "baseball"],
        ["cow", "emergency", "duck"],
        ["garden", "hurricane", "ice"],
        ["milk", "meteor", "mother"],
        ["path", "pollution", "piano"]
    ]
    return random.choice(fallback_sets)

def generate_test_story(vocab_words):
    """Generate a test story with the selected vocabulary words."""
    story_content = f"""Once upon a time, I was exploring a magical forest when my rainbow button started glowing! 

<interaction vocab="{vocab_words[0]}" role="easy">I saw a tiny {vocab_words[0]} carrying a leaf. What do you think it was doing?</interaction>

The {vocab_words[0]} led me to a clearing where I met a friendly {vocab_words[1]} who needed help!

<interaction vocab="{vocab_words[1]}" role="new">The {vocab_words[1]} looked worried. What do you think was wrong?</interaction>

Together, we decided to {vocab_words[2]} through the forest to find a solution.

<interaction vocab="{vocab_words[2]}" role="review">What do you think we might find as we {vocab_words[2]} through the forest?</interaction>

In the end, we helped the {vocab_words[1]} and made a new friend! The {vocab_words[0]} was so happy, it did a little dance.

<interaction vocab="summary">What was your favorite part of my adventure?</interaction>
"""
    
    # Save the story to a temporary file
    with open("test_story.txt", "w") as f:
        f.write(story_content)
    
    return "test_story.txt"

def main():
    # Select random vocabulary words
    vocab_words = select_random_vocab()
    print(f"\nSelected vocabulary words: {vocab_words}")
    
    # Generate test story
    story_file = generate_test_story(vocab_words)
    print(f"\nGenerated test story with file: {story_file}")
    
    # Initialize the interaction handler
    handler = StoryInteractionHandler(
        story_file_path=story_file,
        api_key=os.getenv("OPENAI_API_KEY"),
        max_interaction_depth=3,
        response_length="short"
    )
    
    # The pre-story interaction will automatically start
    # Then the story processing will begin
    
    # Clean up
    if os.path.exists(story_file):
        os.remove(story_file)

if __name__ == "__main__":
    main() 