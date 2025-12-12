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

export interface Event {
    event_id: number,
    event: string,
    date: string | null,
    location: string | null,
}