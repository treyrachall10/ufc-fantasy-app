"""
    -   Holds functions for fantasy scoring
"""

def score_knockdowns(kd):
    """
        -   Scores knockdowns
        -   RETURNS: Float containing scored knockdowns
    """
    return kd * 10

def score_td_landed(td_landed):
    """
        -   Scores takedowns landed
        -   RETURNS: Float containing scored takedowns landed
    """
    return td_landed * 3

def score_sub_att(sub_att):
    """
        -   Scores submission attempts
        -   RETURNS: Float containing scored submission attempts
    """
    return sub_att * 2

def score_ctrl_time(ctrl_time):
    """
        -   Scores control time
        -   RETURNS: Float containing scored control time
    """
    return ctrl_time * .05

def score_win(winner, fighter):
    """
        -   Scores based on if fighter won or not
        -   RETURNS: Float containing scored win points
    """
    if winner == fighter:
        return 20
    else:
        return 0

def score_round_finish(round, time):
    """
        -   Scores based on round fight was finished in
        -   RETURNS: Float containing round bonus
    """
    if round == 5 and time == 300:
        return 0
    elif round == 1:
        return 30
    elif round == 2:
        return 20
    else:
        return 10

def score_time(time):
    """
        -   Scores based on how much time was left in round when finished
        -   RETURNS: Float containing time finish bonus
    """
    return (300 - time) * .03