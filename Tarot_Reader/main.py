import os
import sqlite3
import random
from flask import Flask, render_template, request, url_for, redirect
from openai import OpenAI

app = Flask(__name__)

# Initialize AI client using environment variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def get_db_connection():
    conn = sqlite3.connect('Testdb.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_ai_answer(user_question: str, system_prompt: str) -> str:
    
    if not user_question.strip():
        return "No question was provided."

    # OpenAI call
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_question,
            },
        ],
        max_tokens=200,
        temperature=0.9,
    )

    return completion.choices[0].message.content.strip()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/glossary')
def glossary():
    conn = get_db_connection()
    cards = conn.execute('select id, name from cardsInfo').fetchall()
    conn.close()
    return render_template('glossary.html', cards=cards)

@app.route('/card/<int:card_id>')
def card_detail(card_id):
    conn = get_db_connection()
    card = conn.execute(
        'select id, name, meaning from cardsInfo where id = ?', (card_id,)    
    ).fetchone()
    conn.close()

    return render_template('card_detail.html', card=card)

@app.route('/reader', methods=['GET', 'POST'])
def cards():
    random_card = None
    card_image = None
    ai_answer = None
    user_question = ""
    cards = []
    drawn_cards = []
    system_prompt = (
        "You are a tarot card reading mystic. "
        "Answer the user's question briefly and clearly."
    )

    if request.method == 'POST':
        user_question = request.form.get('Q', '')

        # Get random card from SQLite
        conn = get_db_connection()
        cards = conn.execute('select name, id, meaning from cardsInfo').fetchall()
        conn.close()

        if cards and len(cards) >= 2:
            drawn_cards = random.sample(cards, 2) #array of cards randomely drawn

            card1 = drawn_cards[0]
            card2 = drawn_cards[1]

            random_card = card1
            # .jpg file type is necessary
            card_image = f"images/card_{random_card['id']}.jpg"

            card1_name = card1['name']
            card1_meaning = card1['meaning']
            card2_name = card2['name']
            card2_meaning = card2['meaning']

            system_prompt = (
                "You are a tarot card reading mystic. "
                "Answer the user's question briefly and clearly, and give them a brief reading based on their question. "
                f"The user has drawn two cards. "
                f"Card 1: {card1_name}. Meaning: {card1_meaning}. "
                f"Card 2: {card2_name}. Meaning: {card2_meaning}. "
                "Use both cards together with the user's question to give one short and focused reading."
                )
            
            conn = get_db_connection()
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO readingHistory (
                    card1ID, card2ID, card3ID, card4ID, card5ID, card6ID
                ) VALUES (?, ?, NULL, NULL, NULL, NULL)
                """,
                (card1['id'], card2['id'])
            )

            reading_id = cur.lastrowid

            cur.execute(
            """
            INSERT INTO readingHistoryNumCards (readingID, numCards)
            VALUES (?, ?)
            """,
            (reading_id, 2)
            )

            conn.commit()
            conn.close()

        # Get AI answer based on the user's input
        try:
            ai_answer = get_ai_answer(user_question, system_prompt)
        except Exception as e:
            ai_answer = f"Error calling AI: {e}"

    return render_template(
        'cards.html',
        random_card=random_card,
        drawn_cards=drawn_cards,
        card_image=card_image,
        ai_answer=ai_answer,
        user_question=user_question,
    )

if __name__ == '__main__':
    app.run(debug=True)
