# interactionHandler

Work under [Intuitive Computing Lab](https://intuitivecomputing.github.io/)

Using LLM to handle interactions for storytelling of Early Language Learning

## Overview

This project is an interactive storytelling system designed for early childhood language education. It helps children learn vocabulary through adaptive scaffolding techniques based on their responses during storytelling sessions. The system analyzes a child's input, selects appropriate scaffolding techniques, and generates tailored responses to guide their understanding of story elements and target vocabulary.

## Core Components

1. **StoryInteractionHandler** (`interaction_handler.py`): Main controller that processes story files, manages interactions, and handles the overall story flow. It parses story files containing `<interaction>` tags with optional vocabulary targets, manages conversation depth, and tracks interaction history.

2. **ScaffoldingSelector** (`scaffolding_selector.py`): Analyzes child responses and selects appropriate scaffolding techniques based on a sophisticated complexity analysis algorithm. It uses LLM-based analysis (with GPT-4o-mini) to evaluate responses and determine the optimal scaffolding approach.

3. **ResponseGenerator** (`response_generator.py`): Generates responses using the selected scaffolding techniques, target vocabulary, and appropriate story context. It uses OpenAI's API (GPT-4o) with technique-specific prompts to create developmentally appropriate responses.

## System Logic Flow

The system follows a sophisticated pedagogical process:

1. **Story Parsing**: The system parses story files containing narrative sections interspersed with `<interaction>` tags. These interactions can include target vocabulary words and their roles (new, easy, review).

2. **Complexity Analysis**: The system evaluates the child's response on a scale from 0-10 based on:
   - **Content factors** (high importance):
     - Accuracy: Factually correct answers score at minimum 6/10
     - Reasoning Quality: Attempts at causal reasoning like "because" statements
     - Relevance: On-topic responses score higher than off-topic ones
     - Conceptual Understanding: Demonstration of story concept comprehension
     - Personal Connection: Relating story elements to personal experiences
     - Vocabulary Usage: Correct use of target vocabulary gets +1-2 to score
   
   - **Linguistic factors** (secondary importance):
     - Word count and vocabulary diversity
     - Sentence structure complexity
   
   - **Engagement factors** (high importance):
     - Confidence: Confident responses indicate less need for support
     - Curiosity: Questions show engagement but may indicate need for clarification
     - Emotional Engagement: Expressing feelings about the story

3. **Support Level Determination**:
   - Scores 0-5: HIGH support needed (for simpler, incorrect, or confused responses)
   - Scores 6-10: LOW support needed (for accurate, relevant, confident responses)

4. **Scaffolding Technique Selection**:
   Based on the complexity score and support level, the system selects from these techniques:

   **HIGH Support Techniques**:
   - **Co-Participating**: Joins the child in producing a response by collaboratively exploring ideas, emotions, or possibilities. Models thinking processes and shares cognitive load.
   - **Reducing Choices**: Offers exactly TWO clear, simple alternatives when a child struggles with open-ended questions. Narrows the decision space for complex concepts.
   - **Eliciting**: Provides clear prompts for specific responses to guide children toward relevant story elements they might have missed.

   **LOW Support Techniques**:
   - **Generalizing**: Connects story elements to broader contexts or real-life experiences. Helps children build bridges between narrative and their own knowledge.
   - **Reasoning**: Encourages exploration of why things happen or suggests causal relationships. Promotes critical thinking and logical connections.
   - **Predicting**: Asks the child to anticipate what might happen next based on story events. Engages imagination and develops inference skills.

   **Special Techniques**:
   - **Transition**: Used to acknowledge the child's contribution and smoothly continue the story narrative.
   - **Summary/Closure**: Special technique for concluding stories with a sense of completion.

5. **Context Handling** (Critical Distinction):
   - **Standard Scaffolding Techniques** (co-participating, reducing_choices, eliciting, generalizing, reasoning, predicting):
     - ONLY have access to `context_before` (story elements that have already been introduced)
     - NEVER reference any future story elements or events from `context_after`
     - Must strictly preserve the natural discovery of story elements for the child
     - All questions and responses must be based solely on what has already happened
   
   - **Transition Technique**:
     - Has access to BOTH `context_before` AND `context_after`
     - Can incorporate elements from the upcoming story to create a smooth transition
     - Helps guide the narrative back to the intended story flow
     - Creates a natural bridge between the child's response and what comes next
     - Uses statements rather than questions

6. **Response Generation**: The system creates an appropriate response using the selected technique, incorporating:
   - Brief acknowledgment of the child's input
   - Application of the specific scaffolding technique
   - Natural integration of target vocabulary words
   - Age-appropriate language and perspective
   - First-person narrative perspective as if narrating the story

7. **Follow-up Handling**: The system supports multi-turn interactions with a configurable maximum depth:
   - Tracks conversation depth and history
   - Uses transition technique when reaching maximum depth
   - Preserves context integrity throughout the conversation
   - Maintains vocabulary focus across multiple turns

## Vocabulary Integration

The system seamlessly integrates vocabulary learning:

- **Vocabulary Roles**:
  - **NEW words**: Provides clear context clues and simple definitions
  - **EASY words**: Uses confidently without explanation
  - **REVIEW words**: Reinforces meaning through natural usage

- **Integration Methods**:
  - Incorporates target vocabulary naturally into responses
  - Connects vocabulary to story elements and child's responses
  - Helps children understand words through context and examples
  - Makes vocabulary central to questions or statements
  - Adapts approach based on the vocabulary role

- **Technique-Specific Vocabulary Focus**:
  - Each scaffolding technique has specific guidelines for vocabulary integration
  - Target words are incorporated differently depending on the technique
  - The system tracks vocabulary usage and adapts support accordingly


## Dependencies

- Python 3.x
- OpenAI API (requires API key)
- dotenv (for environment variable management)

## Getting Started

1. Clone this repository
2. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
3. Ensure all system and user prompt files are in the correct directories
4. Run the script with your chosen story file


## Implementation Details

### Story File Format

The system processes story files containing narrative text interspersed with interaction points:

```
Story text begins...

<interaction vocab="rocket" role="new">What do you think might happen next?</interaction>

Story continues...

<interaction vocab="alien" role="review">Why do you think the character did that?</interaction>

Story concludes...

<interaction vocab="summary">What was your favorite part of the story?</interaction>
```

- Each `<interaction>` tag defines a prompt for the child
- Optional `vocab` attribute specifies target vocabulary
- Optional `role` attribute specifies vocabulary role (new, easy, review)
- Special tag `summary` indicates story conclusion




### Usage

```bash
python interaction_handler.py story_file.txt
```

