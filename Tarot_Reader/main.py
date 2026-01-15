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

@app.route('/history')
def history():
    conn = get_db_connection()
    readings = conn.execute(
        """
        SELECT readingID, readingDate,
               card1ID, card2ID, card3ID, card4ID, card5ID, card6ID,
               aiInterpretation
        FROM readingHistory
        ORDER BY readingID DESC
        """
    ).fetchall()
    conn.close()
    return render_template('history.html', readings=readings)

@app.route('/history/<int:reading_id>')
def history_detail(reading_id):
    conn = get_db_connection()

    # Get the reading row
    reading = conn.execute(
        """
        SELECT readingID, readingDate,
               card1ID, card2ID, card3ID, card4ID, card5ID, card6ID,
               aiInterpretation
        FROM readingHistory
        WHERE readingID = ?
        """,
        (reading_id,)
    ).fetchone()

    if reading is None:
        conn.close()
        return "Reading not found", 404

    # Collect card IDs and fetch their details
    card_ids = [
        reading['card1ID'],
        reading['card2ID'],
        reading['card3ID'],
        reading['card4ID'],
        reading['card5ID'],
        reading['card6ID'],
    ]
    card_ids = [cid for cid in card_ids if cid is not None]

    cards = []
    if card_ids:
        placeholders = ",".join("?" for _ in card_ids)
        cards = conn.execute(
            f"SELECT id, name FROM cardsInfo WHERE id IN ({placeholders})",
            card_ids
        ).fetchall()

    conn.close()
    return render_template('history_detail.html', reading=reading, cards=cards)


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
    ai_answer = None
    num_cards = 2
    user_question = ""
    cards = []
    drawn_cards = []
    system_prompt = (
        "You are a tarot card reading mystic. "
        "Answer the user's question briefly and clearly."
    )

    if request.method == 'POST':
        user_question = request.form.get('Q', '')

        num_cards_str = request.form.get('num_cards', '').strip()
        if num_cards_str.isdigit():
            num_cards = int(num_cards_str)
        else:
            num_cards = 2  # fall back to default

        #safty min & max
        if num_cards < 1:
            num_cards = 1
        if num_cards > 6:
            num_cards = 6

        # Get random card from SQLite
        conn = get_db_connection()
        cards = conn.execute('select name, id, meaning from cardsInfo').fetchall()
        conn.close()

        if cards and len(cards) >= num_cards:
            drawn_cards = random.sample(cards, num_cards) #array of cards randomely drawn

            card1 = drawn_cards[0]
            card2 = drawn_cards[1] if len(drawn_cards) > 1 else None

            card_details = []
            for cardNum, card in enumerate(drawn_cards, start=1):
                card_details.append(
                    f"Card {cardNum}: {card['name']}. Meaning: {card['meaning']}."
                )
            card_details_str = " ".join(card_details)
            

            system_prompt = (
                "You are a tarot card reading mystic. "
                "Answer the user's question briefly and clearly, and give them a brief reading based on their question. "
                f"The user has drawn {num_cards_str} card(s). "
                f"{card_details_str} "
                f"Use all of these cards together with the user's question to give one short and focused reading."
                )

        # Get AI answer based on the user's input
        try:
            ai_answer = get_ai_answer(user_question, system_prompt)
            
            conn = get_db_connection()
            cur = conn.cursor()

            drawn_card_ids = [None] * 6
            for i, card in enumerate(drawn_cards):
                if i < 6:
                    drawn_card_ids[i] = card['id']

            cur.execute(
                """
                INSERT INTO readingHistory (
                    card1ID, card2ID, card3ID, card4ID, card5ID, card6ID, aiInterpretation
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (drawn_card_ids[0], drawn_card_ids[1], drawn_card_ids[2], drawn_card_ids[3], drawn_card_ids[4], drawn_card_ids[5], ai_answer)
            )

            reading_id = cur.lastrowid

            cur.execute(
            """
            INSERT INTO readingHistoryNumCards (readingID, numCards)
            VALUES (?, ?)
            """,
            (reading_id, num_cards)
            )

            conn.commit()
            conn.close()
        except Exception as e:
            ai_answer = f"Error calling AI: {e}"

    return render_template(
        'cards.html',
        drawn_cards=drawn_cards,
        ai_answer=ai_answer,
        user_question=user_question,
        num_cards=num_cards,
    )

if __name__ == '__main__':
    app.run(debug=True)
