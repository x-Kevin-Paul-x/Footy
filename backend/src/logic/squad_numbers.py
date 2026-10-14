"""Stable, unique squad numbers shared by reports and match preparation."""


def assign_squad_numbers(players, appearances=None):
    def rating(player):
        attributes = getattr(player, 'attributes', {})
        values = ([v for category in attributes.values() for v in category.values()]
                  if isinstance(attributes, dict) else [a.value for a in attributes])
        return sum(values) / len(values) if values else 0

    ordered = sorted(players, key=lambda p: (
        str(getattr(p, 'squad_role', '')).upper() == 'YOUTH',
        -(appearances or {}).get(p.name, 0),
        -rating(p), p.name))
    used = set()
    for player in ordered:
        number = getattr(player, 'jersey_number', None)
        if isinstance(number, int) and number > 0 and number not in used:
            used.add(number)
        else:
            player.jersey_number = None

    # Traditional first-team positions; an existing allocation stays stable.
    slots = [(1, ('GK',)), (2, ('RB', 'RWB')), (3, ('LB', 'LWB')),
             (4, ('CB',)), (5, ('CB',)), (6, ('CDM', 'DM', 'CM')),
             (7, ('RW', 'RM')), (8, ('CM', 'CDM', 'DM')),
             (9, ('ST', 'CF')), (10, ('CAM', 'AM', 'SS', 'ST', 'CF')),
             (11, ('LW', 'LM'))]
    for number, positions in slots:
        if number in used:
            continue
        candidate = next((p for p in ordered if p.jersey_number is None
                          and p.position.upper() in positions), None)
        if candidate:
            candidate.jersey_number = number
            used.add(number)
    next_number = 12
    for player in ordered:
        if player.jersey_number is None:
            while next_number in used:
                next_number += 1
            player.jersey_number = next_number
            used.add(next_number)


def sync_player_attributes(db, source, target):
    """Persist generated and trained ability, including newly created youth."""
    from database.models import PlayerAttribute
    import json
    target.availability_json = json.dumps({'suspended_matches': getattr(source, 'suspended_matches', 0),
                                          'yellow_cards_accumulator': getattr(source, 'yellow_cards_accumulator', 0),
                                          'is_injured': getattr(source, 'is_injured', False),
                                          'recovery_time': getattr(source, 'recovery_time', 0),
                                          'injury_type': getattr(source, 'injury_type', None)})
    target.contract_json = json.dumps({'release_clause': getattr(source, 'release_clause', None),
                                      'sell_on_clause': getattr(source, 'sell_on_clause', None),
                                      'loan_contract': getattr(source, 'loan_contract', None)})
    existing = {(a.attribute_type, a.sub_attribute): a for a in target.attributes}
    for category, values in source.attributes.items():
        for key, value in values.items():
            attribute = existing.get((category, key))
            if attribute is None:
                attribute = PlayerAttribute(player_id=target.player_id,
                    attribute_type=category, sub_attribute=key, value=value)
                target.attributes.append(attribute)
                db.add(attribute)
            else:
                attribute.value = value
