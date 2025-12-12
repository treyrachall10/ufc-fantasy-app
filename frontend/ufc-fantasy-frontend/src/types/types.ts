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
        wins: number,
        losses: number,
        draws: number
    } | null,
}

export interface FighterWithCareerStats{
    fighter: Fighter,
    total_fights: number;
    wins: number;
    losses: number;
    draws: number;

    ko_tko: number;
    tko_doctor_stoppages: number;
    submissions: number;

    unanimous_decisions: number;
    split_decisions: number;
    majority_decisions: number;
    dq: number;

    sig_str_landed: number;
    sig_str_attempted: number;
    total_str_landed: number;
    total_str_attempted: number;

    td_landed: number;
    td_attempted: number;

    sub_att: number;
    ctrl_time: number;
    reversals: number;

    head_str_landed: number;
    head_str_attempted: number;
    body_str_landed: number;
    body_str_attempted: number;
    leg_str_landed: number;
    leg_str_attempted: number;

    distance_str_landed: number;
    distance_str_attempted: number;
    clinch_str_landed: number;
    clinch_str_attempted: number;
    ground_str_landed: number;
    ground_str_attempted: number;
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