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
  
    striking: {
      total: {
        landed: number;
        attempted: number;
      };
      significant: {
        landed: number;
        attempted: number;
      };
      distance: {
        landed: number;
        attempted: number;
      };
      head: {
        landed: number;
        attempted: number;
      };
      body: {
        landed: number;
        attempted: number;
      };
      leg: {
        landed: number;
        attempted: number;
      };
      clinch: {
        landed: number;
        attempted: number;
      };
      ground: {
        landed: number;
        attempted: number;
      };
    };
  
    grappling: {
      takedowns: {
        landed: number;
        attempted: number;
      };
      sub_att: number;
      reversals: number;
      ctrl_time: number;
    };
  
    opponent: {
      striking: {
        significant: {
          landed: number;
          attempted: number;
        };
      };
      grappling: {
        takedowns: {
          landed: number;
          attempted: number;
        };
        ctrl_time: number;
      };
    };
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