import React from 'react';
import logo from './logo.svg';
import './App.css';
import FightersListPage from './pages/FightersListPage'
import EventsListPage from './pages/EventsListPage'
import FightsListPage from './pages/FightsListPage';
import Navbar from './components/Navbar';

function App() {
  return (
    <>
      <Navbar/>
      <FightsListPage/>
    </>
  );
}

export default App;
