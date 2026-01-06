import os
import sqlite3
import random
from flask import Flask, render_template, request
from openai import OpenAI

app = Flask(__name__)

# Initialize AI client using environment variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_db_connection():
    conn = sqlite3.connect('Testdb.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_ai_answer(user_question: str) -> str:
    
    if not user_question.strip():
        return "No question was provided."

    random_card = random.choice(cards)

    # OpenAI call
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a tarot card reading mystic. "
                    "Answer the user's question briefly and clearly, and give them a brief reading based on thier question."
                    "this is the card that the user has drawn: "
                    
                ),
            },
            {
                "role": "user",
                "content": user_question,
            },
        ],
        max_tokens=200,
        temperature=0.7,
    )

    return completion.choices[0].message.content.strip()

@app.route('/', methods=['GET', 'POST'])
def cards():
    random_card = None
    card_image = None
    ai_answer = None
    user_question = ""

    if request.method == 'POST':
        user_question = request.form.get('Q', '')

        # Get random card from SQLite
        conn = get_db_connection()
        cards = conn.execute('select name, id from cardsInfo').fetchall()
        conn.close()

        if cards:
            random_card = random.choice(cards)
            # Adjust extension to match your files (.jpg)
            card_image = f"images/card_{random_card['id']}.jpg"

        # Get AI answer based on the user's input
        try:
            ai_answer = get_ai_answer(user_question)
        except Exception as e:
            ai_answer = f"Error calling AI: {e}"

    return render_template(
        'cards.html',
        random_card=random_card,
        card_image=card_image,
        ai_answer=ai_answer,
        user_question=user_question,
    )

if __name__ == '__main__':
    app.run(debug=True)
