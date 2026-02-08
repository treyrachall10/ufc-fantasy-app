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
    },
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

export interface FightForFighter {
    fight_id: number,
    event: Event,
    bout: string,
    weight_class: string,
    method: string,
    round: number,
    round_format: string,
    time: number,
    winner: string,
    opponent: string,
    result: string,
}

export interface FantasyFightScore {
    bout: string,
    date: string,
    fight_total_points: number
}

export interface FightStats {
    kd: number;
  
    striking: {
      significant: {
        landed: number;
        attempted: number;
      };
      total: {
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
  }

  export interface RoundFantasyBreakdown {
    points_knockdowns: number,
    points_sig_str_landed: number,
    points_td_landed: number,
    points_sub_att: number,
    points_ctrl_time: number,
    points_reversals: number,
    round_total_points: number,
  }

  export interface RoundFantasy {
    rd_1?: RoundFantasyBreakdown,
    rd_2?: RoundFantasyBreakdown,
    rd_3?: RoundFantasyBreakdown,
    rd_4?: RoundFantasyBreakdown,
    rd_5?: RoundFantasyBreakdown,
  }

  export interface FightLevelFantasyScore {
    points_win: number,
    points_round: number,
    points_time: number,
    fight_total_points: number,
  }

  export interface DetailedFantasyScore {
    round: RoundFantasy,
    fight: FightLevelFantasyScore,
    breakdown: RoundFantasyBreakdown,
    total: number,
  }
  
  export interface HeadToHeadStats {
    fighterA: Fighter;
    fighterB: Fighter;
  
    fighterAFightStats: FightStats;
    fighterBFightStats: FightStats;
    event: Event;

    bout: string;
    winner: string;

    fighterAFantasy: DetailedFantasyScore,
    fighterBFantasy: DetailedFantasyScore
  }

  export interface LeagueInfo {
    league: {
        id: number
        name: string
        status: "SETUP" | "DRAFTING" | "LIVE" | "COMPLETED"
        capacity: number
        join_key: string
        created_at: string
        creator: number
        },
    teams: {
        id: number
        owner: number
        name: string
        created_at: string 
    }[],
    draft: {
        id: number,
        status: "NOT_SCHEDULED" | "PENDING" | "IN_PROGRESS" | "COMPLETED",
        draft_date: string | null
    }
}

  