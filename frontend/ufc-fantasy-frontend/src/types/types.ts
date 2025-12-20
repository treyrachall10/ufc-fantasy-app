/*
    Contains all interfaces for objects
*/

export interface Fighter {
    fighter_id: number,
    first_name: string,
    last_name: string,
    full_name: string,
    nick_name: string | null,
    stance: string | null,
    weight: number | null,
    height: number | null,
    reach: number | null,
    dob: string | null,
    record: {
        wins: {
            total: number,
            ko_tko_wins: number,
            tko_doctor_stoppage_wins: number,
            submission_wins: number,
            unanimous_decision_wins: number,
            split_decision_wins: number,
            majority_decision_wins: number,
            dq_wins: number,
        },
        losses: {
            total: number,
            ko_tko_losses: number,
            tko_doctor_stoppage_losses: number,
            submission_losses: number,
            unanimous_decision_losses: number,
            split_decision_losses: number,
            majority_decision_losses: number,
            dq_losses: number,
        },
        draws: number
    } | null,
}

export interface FighterWithCareerStats {
    fighter: Fighter;
  
    total_fights: number;
    total_fight_time: number;
  
    // Fighter striking
    sig_str_landed: number;
    sig_str_attempted: number;
    total_str_landed: number;
    total_str_attempted: number;
  
    distance_str_landed: number;
    distance_str_attempted: number;
    head_str_landed: number;
    head_str_attempted: number;
    body_str_landed: number;
    body_str_attempted: number;
    leg_str_landed: number;
    leg_str_attempted: number;
    clinch_str_landed: number;
    clinch_str_attempted: number;
    ground_str_landed: number;
    ground_str_attempted: number;
  
    // Fighter grappling
    td_landed: number;
    td_attempted: number;
    sub_att: number;
    reversals: number;
    ctrl_time: number;
  
    // Opponent
    opp_sig_str_landed: number;
    opp_sig_str_attempted: number;
  
    opp_td_landed: number;
    opp_td_attempted: number;
    opp_ctrl_time: number;
  }

export interface Event {
    event_id: number,
    event: string,
    date: string | null,
    location: string | null,
}

export interface Fight {
    fight_id: number,
    event: Event,
    bout: string,
    weight_class: string,
    method: string,
    round: number,
    round_format: string,
    time: number,
    winner: string,
}