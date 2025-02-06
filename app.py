@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
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
            'Julian': {'wins': 5, 'losses': 2, 'run_diff': 19, 'strength': strength_values['Julian']},
            'BenT': {'wins': 5, 'losses': 2, 'run_diff': 13, 'strength': strength_values['BenT']},
            'BenR': {'wins': 4, 'losses': 3, 'run_diff': 18, 'strength': strength_values['BenR']},
            'Kircher': {'wins': 4, 'losses': 3, 'run_diff': -5, 'strength': strength_values['Kircher']},
            'Carbone': {'wins': 3, 'losses': 4, 'run_diff': -6, 'strength': strength_values['Carbone']},
            'HarryKirch': {'wins': 3, 'losses': 4, 'run_diff': -12, 'strength': strength_values['HarryKirch']},
            'Jmo': {'wins': 2, 'losses': 5, 'run_diff': -9, 'strength': strength_values['Jmo']},
            'Tom': {'wins': 2, 'losses': 5, 'run_diff': -18, 'strength': strength_values['Tom']}
        }

        remaining_games = [
            ('HarryKirch', 'BenT'),
            ('Jmo', 'Tom'),
            ('Julian', 'BenR'),
            ('Carbone', 'Kircher'),
            ('Julian', 'Tom'),
            ('BenT', 'Kircher'),
            ('Jmo', 'Carbone'),
            ('BenR', 'HarryKirch'),
            ('BenT', 'Julian'),
            ('Kircher', 'Tom'),
            ('HarryKirch', 'Jmo'),
            ('BenR', 'Carbone')
        ]

        # Run simulation
        sorted_standings, simulated_standings, division_winners, game_results = run_single_simulation(teams, remaining_games)
        scenarios = playoff_scenarios(teams, remaining_games)

        return render_template(
            'index.html',
            standings=sorted_standings,
            simulated_standings=simulated_standings,
            division_winners=division_winners,
            game_results=game_results,
            scenarios=scenarios,
            strength_values=strength_values
        )

    # Initialize strength_values as an empty dictionary for GET requests
    strength_values = {
        'Julian': '',
        'BenT': '',
        'BenR': '',
        'Kircher': '',
        'Carbone': '',
        'HarryKirch': '',
        'Jmo': '',
        'Tom': ''
    }

    return render_template('index.html', strength_values=strength_values)