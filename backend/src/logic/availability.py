"""Apply recorded availability events after serving pre-existing fixture bans."""


def apply_recorded_availability(prepared, result):
    for side, team in (('home', prepared.home_team), ('away', prepared.away_team)):
        players = {player.name: player for player in team.players}
        for event in result.get('events', []):
            player = players.get(event.get('player'))
            if player is None or event.get('team') != side:
                continue
            kind = event.get('type')
            if kind in ('yellow_card', 'red_card'):
                # Recorded statistical totals are updated separately.
                if kind == 'yellow_card':
                    player.yellow_cards_accumulator += 1
                    if player.yellow_cards_accumulator >= 5:
                        player.suspended_matches += 1
                        player.yellow_cards_accumulator = 0
                else:
                    player.suspended_matches += 3
            elif kind == 'injury':
                player.apply_injury(event.get('severity', 'minor'))
