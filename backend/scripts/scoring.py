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
