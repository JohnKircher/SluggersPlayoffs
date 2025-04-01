from flask import Flask, render_template, request, jsonify
import random
import sqlite3
from collections import defaultdict
import copy

app = Flask(__name__)

# Initialize database for storing click count and simulation results
DB_FILE = "clicks.db"

def init_db():
    """Initialize the database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Table for click count
    c.execute('''CREATE TABLE IF NOT EXISTS click_count (id INTEGER PRIMARY KEY, count INTEGER)''')
    c.execute('''INSERT INTO click_count (id, count) SELECT 1, 0 WHERE NOT EXISTS (SELECT 1 FROM click_count)''')
    # Table for simulation results
    c.execute('''
        CREATE TABLE IF NOT EXISTS simulation_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            team TEXT,
            clinch_bye REAL,
            clinch_playoffs REAL,
            miss_playoffs REAL,
            strength REAL
        )
    ''')
    conn.commit()
    conn.close()

def increment_click_count():
    """Increment the simulation click count in the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE click_count SET count = count + 1 WHERE id = 1")
    conn.commit()
    conn.close()

def get_click_count():
    """Retrieve the current click count."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT count FROM click_count WHERE id = 1")
    count = c.fetchone()[0]
    conn.close()
    return count

def save_simulation_results(teams, scenarios, strength_values):
    """Save the simulation results for each team in the database."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    for team, scenario in scenarios.items():
        c.execute('''
            INSERT INTO simulation_results (team, clinch_bye, clinch_playoffs, miss_playoffs, strength)
            VALUES (?, ?, ?, ?, ?)
        ''', (team, scenario['clinch_bye'], scenario['clinch_playoffs'], scenario['miss_playoffs'], strength_values[team]))
    conn.commit()
    conn.close()

def get_accumulated_results():
    """Retrieve accumulated simulation results for each team."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT team,
               AVG(clinch_bye) AS avg_clinch_bye,
               AVG(clinch_playoffs) AS avg_clinch_playoffs,
               AVG(miss_playoffs) AS avg_miss_playoffs,
               AVG(strength) AS avg_strength
        FROM simulation_results
        GROUP BY team
    ''')
    results = c.fetchall()
    conn.close()
    return results

# Ensure the database is initialized at startup
init_db()

# Function to calculate standings with run differential
def calculate_standings(teams, remaining_games, results, run_diffs):
    standings = {team: {'wins': teams[team]['wins'], 'losses': teams[team]['losses'], 'run_diff': teams[team]['run_diff']} for team in teams}
    
    for i, (team1, team2) in enumerate(remaining_games):
        winner, loser = (team1, team2) if results[i] == 1 else (team2, team1)
        run_diff = run_diffs[i]
        
        standings[winner]['wins'] += 1
        standings[winner]['run_diff'] += run_diff
        
        standings[loser]['losses'] += 1
        standings[loser]['run_diff'] -= run_diff
    
    return standings

# Function to run a single simulation
def run_single_simulation(teams, remaining_games):
    results = []
    run_diffs = []
    game_results = []

    for team1, team2 in remaining_games:
        # Calculate win probability based on strength ratings
        strength1 = teams[team1]['strength']
        strength2 = teams[team2]['strength']
        prob_team1_wins = strength1 / (strength1 + strength2)
        
        # Determine the outcome based on the probability
        if random.random() < prob_team1_wins:
            results.append(1)  # team1 wins
            winner, loser = team1, team2
        else:
            results.append(0)  # team2 wins
            winner, loser = team2, team1
        
        # Randomly generate run differential between 1 and 10, with higher values less likely
        run_diff = random.choices(range(1, 11), weights=range(10, 0, -1), k=1)[0]
        run_diffs.append(run_diff)
        
        # Record the game result
        game_results.append(f"{winner} beats {loser} by {run_diff} runs")

    simulated_standings = calculate_standings(teams, remaining_games, results, run_diffs)
    
    # Sort the standings from 1 to 8 based on wins and run differential
    sorted_standings = sorted(simulated_standings.keys(), key=lambda x: (simulated_standings[x]['wins'], simulated_standings[x]['run_diff']), reverse=True)
    
    # Determine division winners (top team in each division gets a bye)
    divisions = {
        'Division A': ['Tom', 'Jmo', 'HarryKirch', 'Kircher'],
        'Division B': ['BenT', 'BenR', 'Carbone', 'Julian']
    }
    division_winners = {}
    for division, teams_in_div in divisions.items():
        sorted_teams = sorted(teams_in_div, key=lambda x: (simulated_standings[x]['wins'], simulated_standings[x]['run_diff']), reverse=True)
        division_winners[division] = sorted_teams[0]  # Top team gets a bye
    
    return sorted_standings, simulated_standings, division_winners, game_results

# Function to determine playoff scenarios
def playoff_scenarios(teams, remaining_games, num_simulations=10000):
    divisions = {
        'Division A': ['Tom', 'Jmo', 'HarryKirch', 'Kircher'],
        'Division B': ['BenT', 'BenR', 'Carbone', 'Julian']
    }
    scenarios = defaultdict(lambda: {'clinch_bye': 0, 'clinch_playoffs': 0, 'miss_playoffs': 0})
    
    for _ in range(num_simulations):
        results = []
        run_diffs = []
        for team1, team2 in remaining_games:
            # Calculate win probability based on strength ratings
            strength1 = teams[team1]['strength']
            strength2 = teams[team2]['strength']
            prob_team1_wins = strength1 / (strength1 + strength2)
            
            # Determine the outcome based on the probability
            if random.random() < prob_team1_wins:
                results.append(1)  # team1 wins
            else:
                results.append(0)  # team2 wins
            
            # Randomly generate run differential between 1 and 10, with higher values less likely
            run_diff = random.choices(range(1, 11), weights=range(10, 0, -1), k=1)[0]
            run_diffs.append(run_diff)
        
        simulated_standings = calculate_standings(teams, remaining_games, results, run_diffs)
        
        # Determine division winners (top team in each division gets a bye)
        division_winners = {}
        wildcards = []
        
        for division, teams_in_div in divisions.items():
            sorted_teams = sorted(teams_in_div, key=lambda x: (simulated_standings[x]['wins'], simulated_standings[x]['run_diff']), reverse=True)
            division_winners[division] = sorted_teams[0]  # Top team gets a bye
            wildcards.extend(sorted_teams[1:])  # Remaining teams go into wildcard pool
        
        # Sort wildcards across both divisions
        sorted_wildcards = sorted(wildcards, key=lambda x: (simulated_standings[x]['wins'], simulated_standings[x]['run_diff']), reverse=True)
        playoff_teams = list(division_winners.values()) + sorted_wildcards[:4]
        
        # Update scenarios for each team
        for team in teams:
            if team in division_winners.values():
                scenarios[team]['clinch_bye'] += 1
            elif team in playoff_teams:
                scenarios[team]['clinch_playoffs'] += 1
            else:
                scenarios[team]['miss_playoffs'] += 1
    
    # Normalize the scenario counts to probabilities
    for team in scenarios:
        total = num_simulations
        scenarios[team]['clinch_bye'] /= total
        scenarios[team]['clinch_playoffs'] /= total
        scenarios[team]['miss_playoffs'] /= total
    
    return scenarios

def calculate_live_probabilities(base_standings, remaining_games, previous_scores, strength_values):
    """
    Determines playoff probabilities based on current standings and entered scores.
    If a game is still 0-0, it is ignored.
    If all games have been played, the playoff outcomes are calculated directly from the standings.
    """
    divisions = {
        'Division A': ['Tom', 'Jmo', 'HarryKirch', 'Kircher'],
        'Division B': ['BenT', 'BenR', 'Carbone', 'Julian']
    }
    scenarios = defaultdict(lambda: {'clinch_bye': 0, 'clinch_playoffs': 0, 'miss_playoffs': 0})

    # Determine which games have been played
    played_games = []
    unplayed_games = []
    for i, (team1, team2) in enumerate(remaining_games):
        score1, score2 = previous_scores.get(i, (0, 0))
        if score1 != 0 or score2 != 0:
            played_games.append((team1, team2, score1, score2))
        else:
            unplayed_games.append((team1, team2))

    # Debugging: Print played and unplayed games
    # print("\n--- Played and Unplayed Games ---")
    # print("Played Games:")
    # for game in played_games:
    #     print(f"{game[0]} vs {game[1]}: {game[2]}-{game[3]}")
    # print("\nUnplayed Games:")
    # for game in unplayed_games:
    #     print(f"{game[0]} vs {game[1]}")

    # If all games have been played, calculate outcomes directly from standings
    if not unplayed_games:
        # Determine division winners (top team in each division gets a bye)
        division_winners = {}
        for division, teams_in_div in divisions.items():
            sorted_teams = sorted(teams_in_div, key=lambda x: (base_standings[x]['wins'], base_standings[x]['run_diff']), reverse=True)
            division_winners[division] = sorted_teams[0]  # Top team gets a bye

        # Debugging: Print division winners
        # print("\n--- Division Winners ---")
        # for division, winner in division_winners.items():
        #     print(f"{division}: {winner} (Wins: {base_standings[winner]['wins']}, Run Diff: {base_standings[winner]['run_diff']})")

        # Determine wildcard teams (next 4 teams across both divisions, excluding division winners)
        all_teams = list(base_standings.keys())
        # Remove division winners from the pool of teams
        teams_eligible_for_wildcards = [team for team in all_teams if team not in division_winners.values()]
        # Sort eligible teams by wins and run differential
        sorted_wildcards = sorted(teams_eligible_for_wildcards, key=lambda x: (base_standings[x]['wins'], base_standings[x]['run_diff']), reverse=True)
        # Select top 4 teams as wildcards
        wildcard_teams = sorted_wildcards[:4]

        # # Debugging: Print wildcard teams
        # print("\n--- Wildcard Teams ---")
        # for i, team in enumerate(wildcard_teams, 1):
        #     print(f"Wildcard {i}: {team} (Wins: {base_standings[team]['wins']}, Run Diff: {base_standings[team]['run_diff']})")

        # Update scenarios for each team
        for team in base_standings:
            if team in division_winners.values():
                scenarios[team]['clinch_bye'] = 1.0
            elif team in wildcard_teams:
                scenarios[team]['clinch_playoffs'] = 1.0
            else:
                scenarios[team]['miss_playoffs'] = 1.0

        return scenarios

    # Otherwise, run simulations for unplayed games
    num_simulations = 10000
    for sim in range(num_simulations):
        # Start with the current base_standings (which already include played games)
        simulated_standings = {
            team: {
                'wins': base_standings[team]['wins'],
                'losses': base_standings[team]['losses'],
                'run_diff': base_standings[team]['run_diff']
            }
            for team in base_standings
        }

        # Simulate the unplayed games
        for team1, team2 in unplayed_games:
            strength1 = strength_values[team1]
            strength2 = strength_values[team2]
            prob_team1_wins = strength1 / (strength1 + strength2)
            if random.random() < prob_team1_wins:
                simulated_standings[team1]['wins'] += 1
                simulated_standings[team2]['losses'] += 1
                run_diff = random.choices(range(1, 11), weights=range(10, 0, -1), k=1)[0]
                simulated_standings[team1]['run_diff'] += run_diff
                simulated_standings[team2]['run_diff'] -= run_diff
            else:
                simulated_standings[team2]['wins'] += 1
                simulated_standings[team1]['losses'] += 1
                run_diff = random.choices(range(1, 11), weights=range(10, 0, -1), k=1)[0]
                simulated_standings[team2]['run_diff'] += run_diff
                simulated_standings[team1]['run_diff'] -= run_diff

            # Debugging: Print Jmo's wins after each game involving him
            # if team1 == 'Jmo' or team2 == 'Jmo':
            #     print(f"\n--- Jmo's Game ---")
            #     print(f"Game: {team1} vs {team2}")
            #     print(f"Result: {team1 if random.random() < prob_team1_wins else team2} wins")
            #     print(f"Jmo's Wins: {simulated_standings['Jmo']['wins']}")

        # # Debugging: Print final standings after each simulation
        # print("\n--- Final Standings After Simulation ---")
        # for team, stats in simulated_standings.items():
        #     print(f"{team}: Wins: {stats['wins']}, Losses: {stats['losses']}, Run Diff: {stats['run_diff']}")

        # Determine division winners (top team in each division gets a bye)
        division_winners = {}
        for division, teams_in_div in divisions.items():
            sorted_teams = sorted(teams_in_div, key=lambda x: (simulated_standings[x]['wins'], simulated_standings[x]['run_diff']), reverse=True)
            division_winners[division] = sorted_teams[0]  # Top team gets a bye

        # # Debugging: Print division winners
        # print("\n--- Division Winners ---")
        # for division, winner in division_winners.items():
        #     print(f"{division}: {winner} (Wins: {simulated_standings[winner]['wins']}, Run Diff: {simulated_standings[winner]['run_diff']})")

        # Determine wildcard teams (next 4 teams across both divisions, excluding division winners)
        all_teams = list(simulated_standings.keys())
        # Remove division winners from the pool of teams
        teams_eligible_for_wildcards = [team for team in all_teams if team not in division_winners.values()]
        # Sort eligible teams by wins and run differential
        sorted_wildcards = sorted(teams_eligible_for_wildcards, key=lambda x: (simulated_standings[x]['wins'], simulated_standings[x]['run_diff']), reverse=True)
        # Select top 4 teams as wildcards
        wildcard_teams = sorted_wildcards[:4]

        # # Debugging: Print wildcard teams
        # print("\n--- Wildcard Teams ---")
        # for i, team in enumerate(wildcard_teams, 1):
        #     print(f"Wildcard {i}: {team} (Wins: {simulated_standings[team]['wins']}, Run Diff: {simulated_standings[team]['run_diff']})")

        # Update scenarios for each team
        for team in simulated_standings:
            if team in division_winners.values():
                scenarios[team]['clinch_bye'] += 1
            elif team in wildcard_teams:
                scenarios[team]['clinch_playoffs'] += 1
            else:
                scenarios[team]['miss_playoffs'] += 1

    # Normalize the scenario counts to probabilities
    for team in scenarios:
        total = num_simulations
        scenarios[team]['clinch_bye'] /= total
        scenarios[team]['clinch_playoffs'] /= total
        scenarios[team]['miss_playoffs'] /= total

    # Debugging: Print final scenarios
    # print("\n--- Final Scenarios ---")
    # for team, scenario in scenarios.items():
    #     print(f"{team}: Clinch Bye: {scenario['clinch_bye'] * 100:.2f}%, Clinch Playoffs: {scenario['clinch_playoffs'] * 100:.2f}%, Miss Playoffs: {scenario['miss_playoffs'] * 100:.2f}%")

    return scenarios

@app.route('/get-click-count', methods=['GET'])
def get_click_count_api():
    """API endpoint to retrieve the current click count."""
    return jsonify({'count': get_click_count()})

@app.route('/get-accumulated-results', methods=['GET'])
def get_accumulated_results_api():
    """API endpoint to retrieve accumulated simulation results."""
    results = get_accumulated_results()
    return jsonify(results)

# Home route
@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        increment_click_count()
        # Get strength values from the form
        strength_values = {
            'Julian': float(request.form['Julian']),
            'BenT': float(request.form['BenT']),
            'BenR': float(request.form['BenR']),
            'Kircher': float(request.form['Kircher']),
            'Carbone': float(request.form['Carbone']),
            'HarryKirch': float(request.form['HarryKirch']),
            'Jmo': float(request.form['Jmo']),
            'Tom': float(request.form['Tom'])
        }

        # Define teams with strength values
        teams = {
            'BenT': {'wins': 5, 'losses': 3, 'run_diff': 23, 'strength': strength_values['BenT']},
            'Tom': {'wins': 5, 'losses': 3, 'run_diff': 19, 'strength': strength_values['Tom']},
            'Jmo': {'wins': 5, 'losses': 3, 'run_diff': 17, 'strength': strength_values['Jmo']},
            'BenR': {'wins': 4, 'losses': 4, 'run_diff': -9, 'strength': strength_values['BenR']},
            'Kircher': {'wins': 4, 'losses': 4, 'run_diff': -1, 'strength': strength_values['Kircher']},
            'Carbone': {'wins': 3, 'losses': 5, 'run_diff': -19, 'strength': strength_values['Carbone']},
            'Julian': {'wins': 3, 'losses': 5, 'run_diff': -15, 'strength': strength_values['Julian']},
            'HarryKirch': {'wins': 3, 'losses': 5, 'run_diff': -15, 'strength': strength_values['HarryKirch']}
        }

        remaining_games = [
            ('HarryKirch', 'Jmo'),
            ('Tom', 'Kircher'),
            ('BenT', 'Carbone'),
            ('BenR', 'Julian'),
            ('Kircher', 'Jmo'),
            ('Tom', 'HarryKirch'),
            ('Julian', 'BenT'),
            ('BenR', 'Carbone')
        ]

        # Run simulation
        sorted_standings, simulated_standings, division_winners, game_results = run_single_simulation(teams, remaining_games)
        scenarios = playoff_scenarios(teams, remaining_games)

        # Save simulation results
        save_simulation_results(teams, scenarios, strength_values)

        # Pass probabilities to the template
        probabilities = scenarios  # Use the scenarios as probabilities

        return render_template(
            'index.html',
            standings=simulated_standings,  # Pass the simulated_standings dictionary
            sorted_standings=sorted_standings,  # Pass the sorted list of team names
            division_winners=division_winners,
            game_results=game_results,
            scenarios=scenarios,
            probabilities=probabilities,
            strength_values=strength_values,
            click_count=get_click_count()
        )

    # Default values for GET request
    division_winners = {
        'Division A': 'Julian',  # Example default value
        'Division B': 'BenT'     # Example default value
    }

    return render_template(
        'index.html',
        click_count=get_click_count(),
        division_winners=division_winners,
        standings={},  # Pass empty standings for initial load
        sorted_standings=[],  # Pass empty sorted_standings for initial load
        game_results=[],  # Pass empty game_results for initial load
        probabilities={}  # Pass empty probabilities for initial load
    )

base_standings = {
            'BenT': {'wins': 5, 'losses': 3, 'run_diff': 23},
            'Tom': {'wins': 5, 'losses': 3, 'run_diff': 19},
            'Jmo': {'wins': 5, 'losses': 3, 'run_diff': 17},
            'BenR': {'wins': 4, 'losses': 4, 'run_diff': -9},
            'Kircher': {'wins': 4, 'losses': 4, 'run_diff': -1},
            'Carbone': {'wins': 3, 'losses': 5, 'run_diff': -19},
            'Julian': {'wins': 3, 'losses': 5, 'run_diff': -15},
            'HarryKirch': {'wins': 3, 'losses': 5, 'run_diff': -15}
    }

remaining_games = [
            ('HarryKirch', 'Jmo'),
            ('Tom', 'Kircher'),
            ('BenT', 'Carbone'),
            ('BenR', 'Julian'),
            ('Kircher', 'Jmo'),
            ('Tom', 'HarryKirch'),
            ('Julian', 'BenT'),
            ('BenR', 'Carbone')
        ]

previous_scores = {i: (0, 0) for i in range(len(remaining_games))}

@app.route('/enter-scores', methods=['GET'])
def enter_scores():
    # Define strength values (you can modify these as needed)
    strength_values = {
        'Julian': 1.0,
        'BenT': 1.0,
        'BenR': 1.0,
        'Kircher': 1.0,
        'Carbone': 1.0,
        'HarryKirch': 1.0,
        'Jmo': 1.0,
        'Tom': 1.0
    }

    # Compute initial probabilities based on base_standings
    probabilities = calculate_live_probabilities(base_standings, remaining_games, previous_scores, strength_values)

    return render_template(
        'enter_scores.html',
        standings=base_standings,
        sorted_standings=sorted(base_standings.keys(), key=lambda x: (base_standings[x]['wins'], base_standings[x]['run_diff']), reverse=True),
        remaining_games=list(enumerate(remaining_games)),
        probabilities=probabilities
    )


@app.route('/update-score', methods=['POST'])
def update_score():
    data = request.get_json()
    team1, team2 = data['team1'], data['team2']
    new_score1, new_score2 = int(data['score1']), int(data['score2'])
    index = data['index']

    # Retrieve the previous score for this game
    old_score1, old_score2 = previous_scores.get(index, (0, 0))

    # Adjust standings by first **removing** the old game result
    if old_score1 > old_score2:  # Old winner
        base_standings[team1]['wins'] -= 1
        base_standings[team2]['losses'] -= 1
    elif old_score2 > old_score1:
        base_standings[team2]['wins'] -= 1
        base_standings[team1]['losses'] -= 1

    base_standings[team1]['run_diff'] -= (old_score1 - old_score2)
    base_standings[team2]['run_diff'] -= (old_score2 - old_score1)

    # Now **apply** the new score
    if new_score1 > new_score2:  # New winner
        base_standings[team1]['wins'] += 1
        base_standings[team2]['losses'] += 1
    elif new_score2 > new_score1:
        base_standings[team2]['wins'] += 1
        base_standings[team1]['losses'] += 1

    base_standings[team1]['run_diff'] += (new_score1 - new_score2)
    base_standings[team2]['run_diff'] += (new_score2 - new_score1)

    # Save the new score
    previous_scores[index] = (new_score1, new_score2)

    # Sort standings
    sorted_standings = sorted(base_standings.keys(), key=lambda x: (base_standings[x]['wins'], base_standings[x]['run_diff']), reverse=True)

    # Define strength values (you can modify these as needed)
    strength_values = {
        'Julian': 1.0,
        'BenT': 1.0,
        'BenR': 1.0,
        'Kircher': 1.0,
        'Carbone': 1.0,
        'HarryKirch': 1.0,
        'Jmo': 1.0,
        'Tom': 1.0
    }

    # Compute **live probabilities** based on entered scores
    probabilities = calculate_live_probabilities(base_standings, remaining_games, previous_scores, strength_values)

    # Render updated tables
    standings_html = render_template('standings_table.html', standings=base_standings, sorted_standings=sorted_standings)
    probabilities_html = render_template('probabilities_table.html', probabilities=probabilities)

    return jsonify({'standings_html': standings_html, 'probabilities_html': probabilities_html})

@app.route('/reset-scores', methods=['POST'])
def reset_scores():
    global previous_scores, base_standings  # Ensure global variables are reset

    # Reset previous scores
    previous_scores = {i: (0, 0) for i in range(len(remaining_games))}

    # Fully reset base_standings to original values
    base_standings = {
            'BenT': {'wins': 5, 'losses': 3, 'run_diff': 23},
            'Tom': {'wins': 5, 'losses': 3, 'run_diff': 19},
            'Jmo': {'wins': 5, 'losses': 3, 'run_diff': 17},
            'BenR': {'wins': 4, 'losses': 4, 'run_diff': -9},
            'Kircher': {'wins': 4, 'losses': 4, 'run_diff': -1},
            'Carbone': {'wins': 3, 'losses': 5, 'run_diff': -19},
            'Julian': {'wins': 3, 'losses': 5, 'run_diff': -15},
            'HarryKirch': {'wins': 3, 'losses': 5, 'run_diff': -15}
    }

    strength_values = {
        'Julian': 1.0,
        'BenT': 1.0,
        'BenR': 1.0,
        'Kircher': 1.0,
        'Carbone': 1.0,
        'HarryKirch': 1.0,
        'Jmo': 1.0,
        'Tom': 1.0
    }

    # Compute new probabilities based on the reset standings
    probabilities = calculate_live_probabilities(base_standings, remaining_games, previous_scores, strength_values)

    # Sort standings
    sorted_standings = sorted(base_standings.keys(), key=lambda x: (base_standings[x]['wins'], base_standings[x]['run_diff']), reverse=True)

    # Render updated tables
    standings_html = render_template('standings_table.html', standings=base_standings, sorted_standings=sorted_standings)
    probabilities_html = render_template('probabilities_table.html', probabilities=probabilities)

    return jsonify({
        'standings_html': standings_html,
        'probabilities_html': probabilities_html
    })


if __name__ == '__main__':
    app.run(debug=True)