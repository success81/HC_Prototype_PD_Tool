from flask import Flask, render_template, request, jsonify
import os
import random
import vertexai
from vertexai.preview.generative_models import GenerativeModel
import markdown2
import logging
import json

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "key.json"
PROJECT_ID = "winter-cogency-436501-g9"
REGION = "us-central1"
vertexai.init(project=PROJECT_ID, location=REGION)

# Loading quotes for UI feedback
LOADING_QUOTES = [
    "Analyzing position requirements...",
    "Structuring duty statements...",
    "Evaluating factor information...",
    "Formatting position description...",
    "Reviewing classification standards...",
    "Applying DOE guidelines...",
    "Organizing content structure...",
    "Validating position elements...",
    "Finalizing document format...",
    "Preparing final output..."
]

def load_examples():
    """Load examples from examples.txt file"""
    try:
        with open('examples.txt', 'r') as file:
            examples = json.load(file)
            logger.info("Successfully loaded examples from examples.txt")
            return examples
    except Exception as e:
        logger.error(f"Error loading examples: {str(e)}")
        return {}

def call_gemini_pro(prompt, temperature=0.7):
    """Call Gemini Pro model with given prompt"""
    try:
        model = GenerativeModel("gemini-1.5-pro-002")
        response = model.generate_content(
            contents=[{"role": "user", "parts": [{"text": prompt}]}],
            generation_config={
                "temperature": temperature,
                "max_output_tokens": 8000,
                "top_p": 1.0,
                "top_k": 40
            }
        )
        return response.text
    except Exception as e:
        logger.error(f"Error calling Gemini: {str(e)}")
        raise

@app.route('/')
def index():
    return render_template('doe_pd_builder.html')

@app.route('/api/generate-questions', methods=['POST'])
def generate_questions():
    try:
        logger.info("Generating questions - request received")
        data = request.json
        duties = data.get('duties', [])
        factors = data.get('factors', {})

        # Create context from duties and factors
        duties_context = "\n".join([
            f"Duty {i+1} ({duty['percentage']}%): {duty['title']} - {duty['description']}"
            for i, duty in enumerate(duties)
        ])

        factors_context = "\n".join([
            f"Factor {i+1}: {factors.get(f'factor{i}', '')}"
            for i in range(1, 10)
        ])

        prompt = f"""As a DOE Position Description expert, generate exactly 15 follow-up questions to gather additional information 
for creating a comprehensive position description. 

Current Information:
DUTIES:
{duties_context}

FACTORS:
{factors_context}

Generate 15 specific questions that will:
1. Fill any gaps in the provided information
2. Clarify technical aspects of the position
3. Explore supervisory relationships
4. Identify specific tools, systems, or equipment used
5. Understand unique challenges or requirements
6. Clarify scope of responsibility
7. Explore decision-making authority
8. Identify critical skills or competencies
9. Understand performance expectations
10. Clarify working conditions

Format each question exactly as:
1- [Question]
2- [Question]
etc.

The questions should be specific, clear, and directly relevant to building a complete DOE position description."""

        logger.info("Calling Gemini for question generation")
        response = call_gemini_pro(prompt, temperature=0.7)
        logger.info("Received response from Gemini")
        
        # Extract questions from response
        questions = [q.strip() for q in response.strip().split('\n') 
                    if q.strip() and any(q.strip().startswith(str(i) + '-') 
                    for i in range(1, 16))][:15]
        
        # Ensure we have exactly 15 questions
        while len(questions) < 15:
            questions.append(f"{len(questions) + 1}- Please provide additional relevant information about this position.")

        return jsonify({
            'questions': questions,
            'loadingQuotes': LOADING_QUOTES
        })
    except Exception as e:
        logger.error(f"Error generating questions: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-pd', methods=['POST'])
def generate_pd():
    try:
        data = request.json
        duties = data['duties']
        factors = data['factors']
        answers = data.get('answers', {})
        examples = load_examples()

        if not examples:
            raise ValueError("Failed to load examples from examples.txt")

        # Format duties context
        duties_context = "\n".join([
            f"Duty {i+1} ({duty['percentage']}%): {duty['title']} - {duty['description']}"
            for i, duty in enumerate(duties)
        ])

        # Format follow-up answers
        answers_context = "\n".join([
            f"Q{i+1}: {answers.get(str(i), 'No answer provided')}"
            for i in range(15)
        ])

        # Generate major duties statement
        duties_prompt = f"""Create a comprehensive major duties statement for a DOE position description using this information:

Duties:
{duties_context}

Additional Context:
{answers_context}

Style examples (Use only as reference for tone and format):
{random.sample(examples['duty_statements'], 2)}

Requirements:
1. Combine all duties into a cohesive narrative
2. Use clear, action-oriented language
3. Follow DOE position description style
4. Focus on key responsibilities and impact
5. Create logical flow between duties
6. Make it original and specific to this position

Create a professional, comprehensive duty statement:"""

        major_duties = call_gemini_pro(duties_prompt, temperature=0.7)

        # Format each factor
        formatted_factors = {}
        for i in range(1, 10):
            factor_key = f'factor{i}'
            factor_prompt = f"""Create a comprehensive Factor {i} statement for this DOE position description based on:

Input Content:
{factors[factor_key]}

Follow-up Information:
{answers_context}

Style examples (Use only as reference for tone and format):
{random.sample(examples[factor_key], 2)}

Requirements:
1. Follow DOE position description style
2. Be specific and detailed
3. Address all key elements of Factor {i}
4. Make it original and position-specific
5. Use appropriate terminology
6. Ensure completeness and clarity

Create a professional factor statement:"""

            formatted_factors[factor_key] = call_gemini_pro(factor_prompt, temperature=0.7)

        # Combine everything into final PD
        pd_content = f"""# Major Duties

{major_duties}

## Individual Duty Statements

{"".join([f"### {d['title']} ({d['percentage']}%)\n{d['description']}\n\n" for d in duties])}

# Position Factors

## Factor 1 - Knowledge Required
{formatted_factors['factor1']}

## Factor 2 - Supervisory Controls
{formatted_factors['factor2']}

## Factor 3 - Guidelines
{formatted_factors['factor3']}

## Factor 4 - Complexity
{formatted_factors['factor4']}

## Factor 5 - Scope and Effect
{formatted_factors['factor5']}

## Factor 6 - Personal Contacts
{formatted_factors['factor6']}

## Factor 7 - Purpose of Contacts
{formatted_factors['factor7']}

## Factor 8 - Physical Demands
{formatted_factors['factor8']}

## Factor 9 - Work Environment
{formatted_factors['factor9']}"""

        return jsonify({
            'html': markdown2.markdown(pd_content),
            'markdown': pd_content,
            'loadingQuotes': LOADING_QUOTES
        })

    except Exception as e:
        logger.error(f"Error generating PD: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)