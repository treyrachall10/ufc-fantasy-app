import React from 'react';
import logo from './logo.svg';
import './App.css';
import FightersListPage from './pages/FightersListPage'
import EventsListPage from './pages/EventsListPage'
import FightsListPage from './pages/FightsListPage';
import AthleteStatsPage from './pages/AthleteStatsPage';
import Navbar from './components/layout/Navbar';
import { Container, CssBaseline } from '@mui/material';
import FightStatsPage from './pages/FightStatsPage';

function App() {
  const fakeFighter = {
    name: "Conor McGregor",
    nickname: "Notorious",
    w: 15,
    l: 3,
    d: 0,
    stance: "Southpaw",
    age: 35,
    height: 175, // cm
    weight: 70, // kg
    reach: 188, // cm
  
    kd: 12,
    sig_str_landed: 865,
    sig_str_attempted: 1724,
    total_str_landed: 1120,
    total_str_attempted: 2250,
    td_landed: 18,
    td_attempted: 62,
    sub_att: 7,
    ctrl_time: 1450,
    reversals: 3,
    head_str_landed: 540,
    head_str_attempted: 1180,
    body_str_landed: 210,
    body_str_attempted: 420,
    leg_str_landed: 115,
    leg_str_attempted: 190,
    distance_str_landed: 750,
    distance_str_attempted: 1500,
    clinch_str_landed: 210,
    clinch_str_attempted: 380,
    ground_str_landed: 160,
    ground_str_attempted: 370,
    wins: 15,
    losses: 3,
    draws: 0,
    total_fights: 18,
    dq: 0,
    majority_decisions: 1,
    split_decisions: 2,
    unanimous_decisions: 6,
    ko_tko: 7,
    submissions: 3,
    tko_doctor_stoppages: 1,
  };
   
  return (
    <>
      <CssBaseline/>

      <Navbar/>
      <Container maxWidth="lg" sx={{py: 3}}>
          <FightStatsPage fightId={10}/>
      </Container>

    </>
  );
}

export default App;
