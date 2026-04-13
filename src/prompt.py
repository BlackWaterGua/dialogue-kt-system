PROMPTS = {}

PROMPTS["DEFAULT_LANGUAGE"] = "English"

PROMPTS["ANNO_KC_PROMPT"] = """-Goal-
Given a dialogue and a list of knowledge points that may be related to it, identify the knowledge points that are both relevant to the dialogue and included in the list.

-Instruction-
1. Do not include knowledge points that are only vaguely or indirectly related. Only select those that are clearly reflected in the dialogue based on their descriptions.
2. Do not rely solely on keyword matching. Focus on the actual meaning and context of the dialogue.
3. The dialogue may not mention knowledge points in exact wording. Use semantic understanding to match paraphrased or implied meanings.
4. The output format should be a list of knowledge point names, like: ["point1", "point2", "point3"].
5. If none of the knowledge points in the list match the dialogue, return an empty list: [].
{examples}
#############################
-Real Data-
######################
Dialogue: {dialogue}
Knowledge_points: {knowledge_points}
######################
Output:

"""

PROMPTS["ANNO_KC_EXAMPLE"] = """######################
-Examples-
######################
Example 1:

Knowledge_points:
[
  {
    "KC_name": "SUPPORT VECTOR MACHINE",
    "KC_description": "Support Vector Machine (SVM) is a supervised machine learning algorithm used for classification and regression tasks, characterized by its use of support vectors and margins."
  },
  {
    "KC_name": "GRADIENT DESCENT",
    "KC_description": "Gradient Descent is an optimization algorithm used to minimize loss functions, although it's typically not used for SVM optimization due to the nature of its formulation."
  }
]

Dialogue:
[
  {
    "role": "user",
    "content": "What is gradient descent? Can you explain it simply?"
  },
  {
    "role": "assistant",
    "content": "Gradient descent is an optimization algorithm used to minimize a loss function."
  }
]
################
Output:
["GRADIENT DESCENT"]
"""

PROMPTS["ANNO_MASTERY_PROMPT"] = """-Goal-
Given a dialogue and a list of knowledge points mentioned in it, along with the user's current mastery status of each knowledge point, your task is to evaluate the user's updated mastery level and learning progress. For each knowledge point, revise the mastery score and append new learning events based on the dialogue.

-Instruction-
1. Each knowledge point is provided as a JSON object. Please extract and update the following fields based on the given information:
- 'KC_name': The name of the knowledge point (keep unchanged)
- 'KC_description': The description of the knowledge point (keep unchanged)
- 'mastery_score': A value between 0 and 1 indicating the user's understanding of the knowledge point.
  - 0 = not yet encountered
  - 0.1–0.4 = attempted but showed misconceptions or errors
  - 0.5–0.7 = partially understood (e.g., correct explanation with small gaps)
  - 0.8–0.9 = mostly understood with minor issues
  - 1 = fully mastered
- 'mastery_history': A time-stamped bullet-point list summarizing the user's interactions and learning progress related to the knowledge point.
  - Each entry should start with a date and describe the event briefly (e.g., questions asked, correct/incorrect answers, improvements, misunderstandings).
  - Only generate mastery_history entries based on the current dialogue. Do not copy or repeat any events that were already recorded in the input User_KC_status.
  - Format: "YYYY/MM/DD: event description"
  - The source_utterance_idx is the index of the utterance in the dialogue.(e.g., 0 = first assistant turn, 1 = first user turn, etc.)
2. Return the analysis results as a JSON list in the following format:
[
  {{
    "KC_name": "KC1",
    "mastery_score": 0.0,
    "mastery_history": [
      {{
        "date": "YYYY/MM/DD",
        "event": "event description",
        "source_utterance_idx": "index of the utterance in the dialogue"
      }},
      ...
    ]
  }}
]
3. Please reply in {language}
{examples}
#############################
-Real Data-
######################
User_KC_status: {user_KC_status}
Dialogue: {dialogue}
######################
Output:

"""

PROMPTS["ANNO_MASTERY_REAL_TIME_PROMPT"] = """-Goal-
Given a dialogue and a list of knowledge points mentioned in it, along with the user's current mastery status of each knowledge point, your task is to evaluate the user's updated mastery level and learning progress. For each knowledge point, revise the mastery score and append new learning events based on the dialogue.
The dialogue is divided into two parts: the “Dialogue already tracked” section, and the “Dialogue not yet tracked” section.
You may refer to the tracked portion for context and continuity, but you must only base your mastery updates and event additions on the untracked part.

-Instruction-
1. Each knowledge point is provided as a JSON object. Please extract and update the following fields based on the given information:
- 'KC_name': The name of the knowledge point (keep unchanged)
- 'KC_description': The description of the knowledge point (keep unchanged)
- 'mastery_score': A value between 0 and 1 indicating the user's understanding of the knowledge point.
  - 0 = not yet encountered
  - 0.1–0.4 = attempted but showed misconceptions or errors
  - 0.5–0.7 = partially understood (e.g., correct explanation with small gaps)
  - 0.8–0.9 = mostly understood with minor issues
  - 1 = fully mastered
- 'mastery_history': A time-stamped bullet-point list summarizing the user's interactions and learning progress related to the knowledge point.
  - Each entry should start with a date and describe the event briefly (e.g., questions asked, correct/incorrect answers, improvements, misunderstandings).
  - Only generate mastery_history entries based on the current dialogue. Do not copy or repeat any events that were already recorded in the input User_KC_status.
  - Format: "YYYY/MM/DD: event description"
  - The source_utterance_idx is the index of the utterance in the dialogue.(e.g., 0 = first assistant turn, 1 = first user turn, etc.)
2. Return the analysis results as a JSON list in the following format:
[
  {{
    "KC_name": "KC1",
    "mastery_score": 0.0,
    "mastery_history": [
      {{
        "date": "YYYY/MM/DD",
        "event": "event description",
        "source_utterance_idx": "index of the utterance in the dialogue"
      }},
      ...
    ]
  }}
]
3. Please reply in {language}
{examples}
#############################
-Real Data-
######################
User_KC_status: {user_KC_status}
Dialogue: {dialogue}
######################
Output:

"""

PROMPTS["ANNO_MASTERY_EXAMPLE"] = """######################
-Examples-
######################
Example 1:

User_KC_status:
[
  {
    "KC_name": "GRADIENT DESCENT",
    "KC_description": "Gradient Descent is an optimization algorithm used to minimize loss functions, although it's typically not used for SVM optimization due to the nature of its formulation.",
    "mastery_score": 0,
    "mastery_history": []
  }
]

Dialogue:
[
  {
    "role": "user",
    "content": "What is gradient descent? Can you explain it simply?",
    "time": "2025/02/27 11:06:32",
  },
  {
    "role": "assistant",
    "content": "Gradient descent is an optimization algorithm used to minimize a loss function.",
    "time": "2025/02/27 11:06:47",
  }
]
################
Output:
[
  {
    "KC_name": "GRADIENT DESCENT",
    "mastery_score": 0.3,
    "mastery_history": [
      {
        "date": "2025/02/27",
        "event": "User inquired about gradient descent, indicating initial exposure.",
        "source_utterance_idx": "0"
      }
    ]
  }
]
"""

PROMPTS["ANNO_MASTERY_REAL_TIME_EXAMPLE"] = """######################
-Examples-
######################
Example 1:

User_KC_status:
[
  {
    "KC_name": "GRADIENT DESCENT",
    "KC_description": "Gradient Descent is an optimization algorithm used to minimize loss functions, although it's typically not used for SVM optimization due to the nature of its formulation.",
    "mastery_score": 0.3,
    "mastery_history": [
      {
        "date": "2025/02/26",
        "event": "User inquired about gradient descent, indicating initial exposure.",
        "source_utterance_idx": "0"
      }
    ]
  }
]

Dialogue:
[
  // ----(Dialogue already tracked)----
  {
    "role": "assistant",
    "content": "Gradient Descent is an optimization method used to minimize loss functions, which we briefly covered last time. Do you remember how it works?",
    "time": "2025/02/27 11:06:32",
  },
  {
    "role": "user",
    "content": "I remember it calculates the gradient of the loss and then moves in the direction that minimizes it, right?",
    "time": "2025/02/27 11:07:47",
  },
  // ----(Dialogue already tracked)----
  // ----(Dialogue not yet tracked)----
  {
    "role": "assistant",
    "content": "Exactly! Do you know what impact the learning rate has on Gradient Descent?",
    "time": "2025/02/27 11:07:53",
  },
  {
    "role": "user",
    "content": "If the learning rate is too large it will oscillate, and if it's too small it will converge very slowly, right?",
    "time": "2025/02/27 11:08:33",
  },
  // ----(Dialogue not yet tracked)----
]
################
Output:
[
  {
    "KC_name": "GRADIENT DESCENT",
    "mastery_score": 0.45,
    "mastery_history": [
      {
        "date": "2025/02/27",
        "event": "User correctly explained the role of learning rate in Gradient Descent, showing improved understanding of its convergence behavior.",
        "source_utterance_idx": "3"
      }
    ]
  }
]
"""